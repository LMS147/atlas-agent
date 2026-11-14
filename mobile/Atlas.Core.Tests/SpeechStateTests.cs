using Atlas.Core;
using Atlas.UI;
using Xunit;
namespace Atlas.Core.Tests;
public sealed class SpeechStateTests : IDisposable
{
    private readonly string directory=Path.Combine(Path.GetTempPath(),"atlas-speech-"+Guid.NewGuid());
    private readonly Voice voice=new();
    private AppState State()=>new(new AtlasRepository(new CacheStore(Path.Combine(directory,"cache.db"))),new CredentialsStub(),new FilesStub(),voice);
    [Fact] public async Task SpeechIsExplicitDoesNotBlockChatAndStopsInBackground()
    {
        var state=State();Assert.False(state.Speaking);Assert.Equal(0,voice.Calls);
        var speaking=state.SpeakAsync("Hello Atlas");Assert.True(state.Speaking);Assert.False(state.Busy);Assert.Equal("Hello Atlas",voice.Text);
        await state.SpeakAsync("Do not overlap");Assert.Equal(1,voice.Calls);
        state.IsActive=false;await speaking;Assert.False(state.Speaking);Assert.True(voice.Cancelled);
        await state.SpeakAsync("Do not speak in background");Assert.Equal(1,voice.Calls);
    }
    [Fact] public async Task StopAndNavigationCancelVoiceAndLongRepliesAreBounded()
    {
        var state=State();var speaking=state.SpeakAsync(new string('x',6500));Assert.Equal(6000,voice.Text.Length);Assert.Contains("6,000",state.Notice);
        await state.NavigateAsync("Settings");await speaking;Assert.False(state.Speaking);
        voice.Cancelled=false;var again=state.SpeakAsync("A second utterance");state.StopSpeaking();await again;Assert.True(voice.Cancelled);
    }
    [Fact] public async Task MissingVoiceEngineLeavesControlsUsable()
    {
        voice.Fail=true;var state=State();await state.SpeakAsync("Hello");Assert.False(state.Speaking);Assert.False(state.Busy);Assert.Contains("text-to-speech",state.Notice);
    }
    [Fact] public async Task OrbWaitsForPlaybackAndNeverInventsListening()
    {
        voice.AutoStart=false;var state=State();
        Assert.Equal("disconnected",CompanionPresence.Mode(state));
        var pending=state.SpeakAsync("Start when ready");
        Assert.True(state.SpeechBusy);Assert.False(state.Speaking);
        Assert.NotEqual("speaking",CompanionPresence.Mode(state));
        voice.Start();Assert.True(state.Speaking);Assert.Equal("speaking",CompanionPresence.Mode(state));
        state.StopSpeaking();Assert.False(state.Speaking);await pending;
        Assert.False(state.SpeechBusy);Assert.NotEqual("listening",CompanionPresence.Mode(state));
        voice.Start();Assert.False(state.Speaking); // late engine event is unsubscribed
    }
    [Fact] public async Task UnrelatedBusyWorkDoesNotPretendTheAiIsThinking()
    {
        var state=State();var gate=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var busy=state.Run(()=>gate.Task);Assert.True(state.Busy);Assert.False(state.ChatThinking);
        gate.SetResult();await busy;
        await state.Run(()=>throw new InvalidOperationException("Operation failed"));
        Assert.Equal("error",CompanionPresence.Mode(state));Assert.Equal("Needs attention",CompanionPresence.Label(state));
    }
    public void Dispose(){Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();if(Directory.Exists(directory))Directory.Delete(directory,true);}
    private sealed class Voice:IAtlasSpeechPlayback
    {
        public event Action<bool>? PlaybackChanged;
        public bool AutoStart=true;
        public void Start()=>PlaybackChanged?.Invoke(true);
        public string Text="";public int Calls;public bool Cancelled,Fail;
        public async Task SpeakAsync(string text,CancellationToken cancellationToken)
        {Calls++;Text=text;if(Fail)throw new NotSupportedException();if(AutoStart)Start();try{await Task.Delay(Timeout.Infinite,cancellationToken);}catch(OperationCanceledException){Cancelled=true;throw;}}
    }
    private sealed class CredentialsStub:ICredentialStore{public Task<Credentials?> LoadAsync()=>Task.FromResult<Credentials?>(null);public Task SaveAsync(Credentials value)=>Task.CompletedTask;public void Clear(){}}
    private sealed class FilesStub:IDeviceFiles{public Task<(string Name,byte[] Content)?> PickAsync()=>Task.FromResult<(string,byte[])?>(null);public Task SaveAsync(string name,byte[] content)=>Task.CompletedTask;public Task<bool> ConfirmAsync(string title,string message)=>Task.FromResult(false);}
}
