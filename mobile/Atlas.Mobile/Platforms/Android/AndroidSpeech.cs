using Android.OS;
using Android.Speech.Tts;
using TextToSpeech = Android.Speech.Tts.TextToSpeech;
namespace Atlas.Mobile;

internal static class AndroidSpeech
{
    public static async Task PlayAsync(string text,Action<bool> playback,CancellationToken token)
    {
        TextToSpeech? engine=null;
        using var init=new InitListener();
        using var listener=new ProgressListener(playback);
        try
        {
            token.ThrowIfCancellationRequested();
            await MainThread.InvokeOnMainThreadAsync(()=>{engine=new TextToSpeech(Android.App.Application.Context,init);});
            var status=await init.Ready.Task.WaitAsync(TimeSpan.FromSeconds(15),token);
            if(status!=OperationResult.Success)throw new NotSupportedException("TTS initialization failed.");
            await MainThread.InvokeOnMainThreadAsync(()=>engine!.SetOnUtteranceProgressListener(listener));
            // Stop immediately on backgrounding/cancel, even during initialization.
            using var cancellation=token.Register(()=>MainThread.BeginInvokeOnMainThread(()=>engine?.Stop()));
            var limit=Math.Max(1,Math.Min(3500,TextToSpeech.MaxSpeechInputLength-1));
            for(var offset=0;offset<text.Length;)
            {
                token.ThrowIfCancellationRequested();
                var length=Math.Min(limit,text.Length-offset);
                // Keep UTF-16 surrogate pairs intact across utterance boundaries.
                if(offset+length<text.Length && char.IsHighSurrogate(text[offset+length-1]))length--;
                var chunk=text.Substring(offset,length);offset+=length;
                var id=Guid.NewGuid().ToString("N");var completion=listener.Begin(id);
                var result=await MainThread.InvokeOnMainThreadAsync(()=>
                {
                    using var parameters=new Bundle();parameters.PutFloat(TextToSpeech.Engine.KeyParamVolume,.85f);
                    engine!.SetPitch(1f);
                    return engine.Speak(chunk,QueueMode.Flush,parameters,id);
                });
                if(result!=OperationResult.Success)throw new NotSupportedException("TTS rejected the utterance.");
                await completion.WaitAsync(TimeSpan.FromMinutes(5),token);
            }
        }
        finally
        {
            listener.End();
            // Keep callbacks alive until the engine has stopped and shut down.
            if(engine is not null)await MainThread.InvokeOnMainThreadAsync(()=>{engine.Stop();engine.Shutdown();engine.Dispose();});
        }
    }
    private sealed class InitListener:Java.Lang.Object,TextToSpeech.IOnInitListener
    {
        public TaskCompletionSource<OperationResult> Ready {get;}=new(TaskCreationOptions.RunContinuationsAsynchronously);
        public void OnInit(OperationResult status)=>Ready.TrySetResult(status);
    }
    private sealed class ProgressListener(Action<bool> playback):UtteranceProgressListener
    {
        private readonly object sync=new();
        private string? current;
        private TaskCompletionSource? completion;
        public Task Begin(string id){lock(sync){current=id;completion=new(TaskCreationOptions.RunContinuationsAsynchronously);return completion.Task;}}
        public override void OnStart(string? id){lock(sync){if(id==current)playback(true);}}
        public override void OnDone(string? id){lock(sync){if(id!=current)return;playback(false);completion?.TrySetResult();current=null;}}
        [Obsolete("Required compatibility callback for Android TTS engines.")]
        public override void OnError(string? id){lock(sync){if(id!=current)return;playback(false);completion?.TrySetException(new NotSupportedException("TTS playback failed."));current=null;}}
        public override void OnStop(string? id,bool interrupted){lock(sync){if(id!=current)return;playback(false);completion?.TrySetCanceled();current=null;}}
        public void End(){lock(sync){current=null;playback(false);completion?.TrySetCanceled();}}
    }
}
