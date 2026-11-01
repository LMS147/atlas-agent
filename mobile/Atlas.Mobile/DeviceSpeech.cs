using Atlas.UI;
using Microsoft.Maui.Media;
namespace Atlas.Mobile;
public sealed class DeviceSpeech : IAtlasSpeech
{
    public Task SpeakAsync(string text,CancellationToken cancellationToken)=>
        MainThread.InvokeOnMainThreadAsync(()=>TextToSpeech.Default.SpeakAsync(text,new SpeechOptions { Pitch=1f,Volume=.85f },cancellationToken));
}
