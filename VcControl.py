from xmlrpc.client import boolean
import discord
import asyncio
from API.tenorAPIget import get_tenor_gif
from SongManager import SongManager
from const.options import ffmpeg_error_log, default_init_vol, leaving_gif_search_list
from const.helper import *
from const.SongInfo import SongInfo
from exceptions import DJExceptions
import SourceCompile
from API.ytAPIget import *
import random
import ServersHub

from API.ytAPIget import yt_search_suggestions

DJAuthor: str = 'DJ'

class VcControl():
    def __init__(self, id, g_name, vc, loop) -> None:
        self.vc: discord.VoiceClient = vc
        self.songManager = SongManager()
        self.asyncLoop = loop
        # self.nowplaying: bool = False
        self.playingSong: SongInfo = None
        self.playingInfo: tuple[SongInfo, str] = None
        self.skip_author = None
        self.dj = True
        self.started = False
        self.djReadied: tuple[str, dict, bool] = None # (yt_link, play_options, suggested)
        self.displaySuggestions: list[SongInfo] = []
        
        self.djSuggestCount = 0
        self.djSuggestInterval = 4
        
        # updated (prevent fetching all data every second)
        self.updated = False
        
        self.guild_id = id
        self.guild_name = g_name
        self.Hub = ServersHub.ServersHub
        
        print("VCcontrol inited")
        pass
    
    def getServerControl(self):
        return self.Hub.getControl(self.guild_id)
    
    # --------------------------------------------------------------------------- # 
    # ----------------------------- GETTERS ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    def getPlayingInfo(self) -> tuple[SongInfo, str]:
        return self.playingInfo
    
    def getNowplaying(self) -> (SongInfo):
        return self.playingSong
    
    def getSuggestions(self) -> list[SongInfo]:
        return self.displaySuggestions
    
    def updatePlayingInfo(self):
        info = self.getNowplaying()
        if info is None: return 
        
        newInfo = self.Hub.djdb.db_get(info.get(SongAttr.vID))
        self.playingSong = newInfo
        _, player = self.getPlayingInfo()
        self.playingInfo = (newInfo, player)

    def getQueue(self):
        '''list/ playlist'''
        return self.songManager.getPlaylist()
    
    def getTitleQueue(self):
        '''list/ playlist'''
        return [ info.Title for source, info, author in self.songManager.getPlaylist() ]

    
    # --------------------------------------------------------------------------- # 
    # ----------------------------- LOOP ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    def startPlayLoop(self):
        '''Add exec loop to current asyncio loop'''
        self.asyncLoop.create_task(self.execLoop())

    async def execLoop(self):
        '''execute actions periodically, manage conflict actions and terminate vc controls'''
        # prevent multiple exec loop
        if self.started:
            return 
        
        self.started = True
        try:
            while(self.vc is not None):
                self.exec()
                await asyncio.sleep(1)
        except Exception as e:
            error_log_e(e)
            
        print("Exec Loop ended")
        
        self.started = False

    def exec(self):
        ''' Executed per second '''
        just_skipped = self.skip_author is not None
        
        ##### check if vc is still playing or skipped (song ended) 
        ##### NOTIFY SERVER SONG ENDED, CAN ALSO LEAVE IF NO ONE IN THE CHANNEL
        if not self.vc.is_playing() or just_skipped:
            
            # trigger song ended on server control
            if self.playingSong is not None: self.getServerControl().songEnded(self.playingSong.get(SongAttr.vID), skipped=just_skipped)
            
            # Reset playing song internally to indicate song ended
            self.playingSong = None
            self.playingInfo = None
            
            # auto leave when no one else in vchannel
            members = self.vc.channel.members
            if len(members) == 1: # CAN ALSO CHECK FOR THAT ONE USER IS THE BOT
                self.getServerControl().leave()
                return
            
        ##### NOTHING IS PLAYING, AND SOMETHING IS IN QUEUE, then play queued song
        if self.playingSong is None and len(self.songManager.getPlaylist()) > 0:
            
            # Get next queued song and PLAY
            source, songInfo, player = self.songManager.next()
            # songInfo.player = player # DO NOT INCLUDE PLAYER IN SONG INFO
            self.playingSong = songInfo
            self.playingInfo = (songInfo, player)
            self.vc.play(source)
            
            # RESET DJ SUGGESTION
            self.djReadied = None
            # RESET SKIP AUTHOR
            self.skip_author = None
            
            # add play history
            vID = self.playingSong.get(SongAttr.vID)
            self.Hub.djdb.add_history(vID, self.guild_id, self.guild_name, str(player))
            # trigger song started on server control
            self.getServerControl().songStarted(vID)
            
        ##### CURRENTLY PLAYING, OR NOTHING PLAYING BUT NOTHING IN QUEUE
        else:
            # PREPARE SOMETHING FOR THE NEXT SONG (RANDOM SONG)
            if self.dj and self.djReadied == None and len(self.songManager.getPlaylist()) == 0:
                self.djReadied = self.djExec()
            
            # DJ already prepared song, NOTHING CURRENTLY PLAYING, then queue DJ readied song
            # nothing playing && queue empty && dj enabled && dj readied song
            if (self.dj and self.djReadied != None and self.playingSong is None 
                and len(self.songManager.getPlaylist()) == 0):
                
                (yt_link, options, suggested) = self.djReadied
                # Do not play dj recommendation if just skipped
                if not (suggested and just_skipped): 
                    try: 
                        self.getServerControl().play(yt_link, **options)
                    except DJExceptions.DJBannedException:
                        pass
                self.djReadied = None
                
            # currently playing
            # do idle task
            
                
                
    # --------------------------------------------------------------------------- # 
    # ----------------------------- DJ ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 
    def getDJNext(self):
        return self.djReadied
    
    def djExec(self):
        playingVid = getattr(self.playingSong, SongAttr.vID) if self.playingSong else None
        vid = None
        suggested = False
        while vid == None:
            self.djSuggestCount += 1
            if self.djSuggestCount >= self.djSuggestInterval and playingVid:
                vid = self.getDJSongFromSuggestions(playingVid)
                print("DJ SUGGESTING yt suggestions:", vid)
                self.djSuggestCount = 0
                suggested = True
            else:            
                vid = self.Hub.djdb.find_rand_song()
                print("DJ SUGGESTING rand db song:", vid)
    
        return (
            vid_to_url(vid),
            {
                "newDJable": True,
                "author": DJAuthor 
            },
            suggested
        )
    
    def getDJSongFromSuggestions(self, vidToSuggestFrom):
        '''Find dj source from youtube suggestions'''
        vid = None
        suggestions_list = yt_search_suggestions(vidToSuggestFrom)
        if len(suggestions_list) > 0:
            suitableSongs = VcControl.filterSuitableSuggestion(suggestions_list)
            self.displaySuggestions = suitableSongs.copy()
            self.getServerControl().suggestionUpdated()
            suitableVids = [getattr(s, SongAttr.vID) for s in suitableSongs]
            
            random.shuffle(suitableVids)
            
            for candidateVid in suitableVids:
                # only suggest this if it is djable
                djable = self.Hub.djdb.find_djable(candidateVid)
                # None: means djdb does not contain that vid (new song, play it with djable as default)
                if djable or djable is None:
                    vid = candidateVid
                    info, inserted = SourceCompile.yt_search_and_insert(vid, use_vID = True, newDJable = True)
                    return vid
        return None
        
    def filterSuitableSuggestion(songs, max_mins = 10) -> list[SongInfo]:
        '''
        Find the most suitable suggestion from list
        songs: list(SongInfo)   - list of suggested songs
        max_mins: int           - maximum minutes of the suggested song should have
        Returns list of suitable vIDs : [str]
        '''

        suitable = []
        for song in songs:
            # 1. the song cant be banned
            if is_banned(getattr(song, SongAttr.Title)):
                continue
            
            # 2. the song cant be over 10 mins
            #  individual (detailed) search
            song_detailed = yt_search(getattr(song, SongAttr.vID), use_vID = True) # TODO: update and insert detailed song info (in idle operation?)
            if song_detailed.duration > (max_mins * 60):
                continue

            # 3. the song should have similar title
            if song_is_live(getattr(song, SongAttr.Title)):
                continue

            # 3. the song should have similar title
            print("suitable song: " + str(song))
            # suitable.append(getattr(song, SongAttr.vID))
            suitable.append(song)

        return suitable

    # --------------------------------------------------------------------------- # 
    # ----------------------------- ACTIONS ---------------------------------------- # 
    # --------------------------------------------------------------------------- # 

    def set_dj_type(self, dj: boolean):
        self.dj = dj
        # initiate loop
        if dj: 
            self.startPlayLoop()
            self.djSuggestCount = 0
        # stop otherwise
        else: self.stop()

    def addSong(self, source, songInfo, player, insert = False):
        print("add song")
        print(source)
        print(player)
        self.songManager.add(source, songInfo, player, insert)
        # start loop
        self.startPlayLoop()

    def skip(self, author=None):
        self.vc.stop()
        self.skip_author = author
        self.playingInfo = None
        self.playingSong = None

    def remove(self, title_substr, author):
        '''remove_track'''
        self.songManager.remove(title_substr)

    def clear(self):
        self.songManager.clear()

    def stop(self):
        self.vc.stop()
        self.playingInfo = None
        self.playingSong = None
        # clear all queue?? 
        # disconnect??
        pass
        
    def disconnect(self):
        self.dj = None
        self.stop()
        # disconnect vc
        self.asyncLoop.create_task(self.vc.disconnect())
        self.vc = None