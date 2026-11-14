namespace Atlas.UI;

/// <summary>Only actual application events select a presence state. No synthetic listening.</summary>
public static class CompanionPresence
{
    public static string Mode(AppState state) => state.Error is not null ? "error" :
        state.Speaking ? "speaking" :
        !state.Connected || state.Repo.Offline ? "disconnected" :
        state.ChatThinking ? "thinking" : "idle";
    public static string Label(AppState state) => Mode(state) switch
    {
        "error" => "Needs attention",
        "disconnected" => "Disconnected",
        "speaking" => "Speaking",
        "thinking" => "Thinking",
        _ => state.SpeechBusy ? state.PlaybackFeedbackAvailable?"Preparing voice…":"Voice playback requested" : "Ready"
    };
}
