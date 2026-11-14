using Atlas.Core;
namespace Atlas.UI;

/// <summary>Shared C# presentation state; native capabilities are injected at the host.</summary>
public sealed class AppState(AtlasRepository repository, ICredentialStore credentials, IDeviceFiles files, IAtlasSpeech? speech = null)
{
    public AtlasRepository Repo { get; } = repository;
    public IDeviceFiles DeviceFiles { get; } = files;
    public event Action? Changed;
    public bool Busy { get; private set; }
    public bool DrawerOpen { get; private set; }
    public void SetDrawer(bool open){if(DrawerOpen==open)return;DrawerOpen=open;Notify();}
    private bool active=true;
    public bool IsActive { get=>active; set {if(active==value)return;active=value;if(!value)StopSpeaking();Notify();} }
    private CancellationTokenSource? speechStop;
    private bool playbackActive;
    public bool SpeechBusy=>speechStop is not null;
    public bool Speaking=>SpeechBusy && playbackActive;
    public bool PlaybackFeedbackAvailable=>speech is IAtlasSpeechPlayback;
    public bool ChatThinking=>Busy && Repo.Messages.Any(x=>x.Role=="user" && x.Delivery==Delivery.Pending);
    public bool SpeechAvailable=>speech is not null;
    public void StopSpeaking(){speechStop?.Cancel();if(playbackActive){playbackActive=false;Notify();}}
    public async Task SpeakAsync(string text)
    {
        if(!IsActive || speechStop is not null || string.IsNullOrWhiteSpace(text))return;
        if(speech is null){Success("Voice playback is unavailable in this host.");return;}
        var stop=new CancellationTokenSource();speechStop=stop;playbackActive=false;
        var playback=speech as IAtlasSpeechPlayback;
        void PlaybackChanged(bool playing)
        {
            if(!ReferenceEquals(speechStop,stop) || stop.IsCancellationRequested || !IsActive)return;
            playbackActive=playing;Notify();
        }
        if(playback is not null)playback.PlaybackChanged+=PlaybackChanged;
        Notify();
        try
        {
            if(text.Length>6000){text=text[..6000];Notice="Reading the first 6,000 characters. You can stop playback at any time.";Notify();}
            await speech.SpeakAsync(text,stop.Token);
        }
        catch(OperationCanceledException) when(stop.IsCancellationRequested){}
        catch(Exception){Notice="Voice playback is unavailable. Check that a text-to-speech voice is installed on your device.";}
        finally{if(playback is not null)playback.PlaybackChanged-=PlaybackChanged;playbackActive=false;speechStop=null;stop.Dispose();Notify();}
    }
    public string? Error { get; private set; }
    public string? Notice { get; private set; }
    public Func<Task<bool>>? BackHandler { get; set; }
    public async Task BackAsync()
    {
        if(DrawerOpen){SetDrawer(false);return;}
        if(Busy)return;
        if(BackHandler is not null && await BackHandler())return;
        if(Connected && Page!="Chat")await NavigateAsync("Chat");
    }
    public bool Initialized { get; private set; }
    public string Page { get; private set; } = "Setup";
    public string ServerUrl { get; set; } = AtlasApi.DefaultUrl;
    public bool Connected => Repo.Connected;
    public void Notify()=>Changed?.Invoke();
    public async Task<bool> Run(Func<Task> action)
    {
        if(Busy)return false;
        Busy=true;Error=null;Notice=null;Notify();
        try{await action();return true;}
        catch(Exception e){Error=AtlasRepository.Friendly(e);return false;}
        finally{Busy=false;Notify();}
    }
    public async Task InitializeAsync()
    {
        if(Initialized)return;Initialized=true;Repo.Changed+=Notify;
        await Run(async()=>
        {
            var saved=await credentials.LoadAsync();
            if(saved is null)return;
            ServerUrl=saved.Url;await Repo.ConnectAsync(saved.Url,saved.Token);Page="Chat";
            if(!Repo.Offline)await Repo.HistoryAsync();
        });
    }
    public Task<bool> ConnectAsync(string token,bool remember)=>Run(async()=>
    {
        await Repo.ConnectAsync(ServerUrl,token);
        ServerUrl=Repo.Url;
        if(remember)await credentials.SaveAsync(new Credentials(ServerUrl,token.Trim()));else credentials.Clear();
        Page="Chat";
        if(!Repo.Offline)await Repo.HistoryAsync();
    });
    public Task<bool> NavigateAsync(string page)=>Run(async()=>
    {
        if(page is not ("Chat" or "Atlas"))StopSpeaking();
        Page=page;
        if(page=="Conversations")await Repo.RefreshConversationsAsync();
        if(page=="Memory")await Repo.RefreshMemoryAsync();
    });
    public void Success(string text){Notice=text;Notify();}
    public void Disconnect()
    {
        if(Busy)return;
        DrawerOpen=false;StopSpeaking();credentials.Clear();Repo.Disconnect();Page="Setup";Error=null;Notice=null;Notify();
    }
}
