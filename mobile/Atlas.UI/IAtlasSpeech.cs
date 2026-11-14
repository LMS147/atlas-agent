namespace Atlas.UI;
public interface IAtlasSpeech
{
    Task SpeakAsync(string text, CancellationToken cancellationToken);
}

/// <summary>Optional engine feedback. A queued request is not confirmed playback.</summary>
public interface IAtlasSpeechPlayback : IAtlasSpeech
{
    event Action<bool>? PlaybackChanged;
}
