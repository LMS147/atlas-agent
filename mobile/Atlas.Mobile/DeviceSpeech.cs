using Atlas.UI;
using Microsoft.Maui.Media;
namespace Atlas.Mobile;

#if ANDROID
/// <summary>Uses the installed Android TTS engine; animation starts at OnStart,
/// not when a request is queued. No audio recording or added permissions.</summary>
public sealed class DeviceSpeech : IAtlasSpeechPlayback
{
    public event Action<bool>? PlaybackChanged;
    public Task SpeakAsync(string text,CancellationToken cancellationToken)=>
        AndroidSpeech.PlayAsync(text,playing=>PlaybackChanged?.Invoke(playing),cancellationToken);
}
#else
public sealed class DeviceSpeech : IAtlasSpeech
{
    // MAUI's other hosts do not expose a confirmed start event or audio samples.
    // Playback stays supported, but the orb does not invent a speaking pulse.
    public Task SpeakAsync(string text,CancellationToken cancellationToken)=>
        MainThread.InvokeOnMainThreadAsync(()=>TextToSpeech.Default.SpeakAsync(text,new SpeechOptions { Pitch=1f,Volume=.85f },cancellationToken));
}
#endif
