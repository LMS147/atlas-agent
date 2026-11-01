namespace Atlas.UI;
public interface IAtlasSpeech
{
    Task SpeakAsync(string text, CancellationToken cancellationToken);
}
