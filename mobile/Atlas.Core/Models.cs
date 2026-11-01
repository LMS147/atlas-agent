namespace Atlas.Core;

public sealed record Health(string Status, string Version = "", long UptimeSeconds = 0);
public sealed record Conversation(string Id, string Title, long CreatedAt, long UpdatedAt, int MessageCount, string Preview, bool Deleted = false)
{
    public bool ServerAvailable { get; init; } = true;
    public long? BeforeCursor { get; init; }
    public bool HasMore { get; init; }
}
public sealed record Transcript(long Seq, string Id, string RequestId, string Role, string Text, long CreatedAt);
public sealed record MessagePage(List<Transcript> Items, bool HasMore, long? NextBefore);
public sealed record RequestStatus(string RequestId, string Status, string? Reply);
public sealed record MemoryItem(string Id, string Section, string Fact);
public sealed record Profile(string Name, string Content);
public sealed record FileItem(string Name, string Path, bool Directory, long SizeBytes, bool Writable);
public sealed record FileDocument(string Path, string Content, string Revision, bool Writable);
public sealed record CompactPlan(string Revision, int BeforeChars, int AfterChars, int RemovedEntries);
public sealed record Ram(long TotalBytes, long AvailableBytes, long UsedBytes);
public sealed record Disk(long TotalBytes, long UsedBytes, long FreeBytes);
public sealed record ServiceMetrics(int Pid, long UptimeSeconds, int Threads, long Requests, long Errors, int ActiveRequests);
public sealed record Monitoring(long SampledAt, double? DeviceCpuPercent, double ProcessCpuPercent, Ram? Ram, long? ProcessRssBytes,
    Disk? Storage, long? DeviceUptimeSeconds, ServiceMetrics Service, List<string> Unavailable);
public enum Delivery { Pending, Sent, Recoverable, NotReceived, Failed }
public sealed record LocalMessage(string Id, string ConversationId, string RequestId, string Role, string Text, long CreatedAt,
    Delivery Delivery = Delivery.Sent, string? Error = null);
public sealed record Selection(string Id);
public sealed record Credentials(string Url, string Token);
public interface ICredentialStore
{
    Task<Credentials?> LoadAsync();
    Task SaveAsync(Credentials value);
    void Clear();
}
public interface IDeviceFiles
{
    Task<(string Name, byte[] Content)?> PickAsync();
    Task SaveAsync(string name, byte[] content);
    Task<bool> ConfirmAsync(string title, string message);
}
