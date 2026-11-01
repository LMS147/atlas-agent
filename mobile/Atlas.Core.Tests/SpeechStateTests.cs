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
    public void Dispose(){Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();if(Directory.Exists(directory))Directory.Delete(directory,true);}
    private sealed class Voice:IAtlasSpeech
    {
        public string Text="";public int Calls;public bool Cancelled,Fail;
        public async Task SpeakAsync(string text,CancellationToken cancellationToken)
        {Calls++;Text=text;if(Fail)throw new NotSupportedException();try{await Task.Delay(Timeout.Infinite,cancellationToken);}catch(OperationCanceledException){Cancelled=true;throw;}}
    }
    private sealed class CredentialsStub:ICredentialStore{public Task<Credentials?> LoadAsync()=>Task.FromResult<Credentials?>(null);public Task SaveAsync(Credentials value)=>Task.CompletedTask;public void Clear(){}}
    private sealed class FilesStub:IDeviceFiles{public Task<(string Name,byte[] Content)?> PickAsync()=>Task.FromResult<(string,byte[])?>(null);public Task SaveAsync(string name,byte[] content)=>Task.CompletedTask;public Task<bool> ConfirmAsync(string title,string message)=>Task.FromResult(false);}
}
