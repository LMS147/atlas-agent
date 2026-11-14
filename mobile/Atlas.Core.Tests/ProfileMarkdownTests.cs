using Atlas.UI.Components;
using Xunit;
namespace Atlas.Core.Tests;
public sealed class ProfileMarkdownTests
{
    [Fact]
    public void ProfileUsesSemanticHeadingsListsEmphasisAndCode()
    {
        var html=ProfileMarkdown.Render("# Atlas\n\nA **personal** workspace.\n\n- Keep context\n- Stay *helpful*\n\n1. Think\n2. Act\n\n```text\n<safe>\n```");
        Assert.Contains("<h1>Atlas</h1>",html);
        Assert.Contains("<strong>personal</strong>",html);
        Assert.Contains("<ul><li>Keep context</li><li>Stay <em>helpful</em></li></ul>",html);
        Assert.Contains("<ol><li>Think</li><li>Act</li></ol>",html);
        Assert.Contains("<pre><code>&lt;safe&gt;",html);
    }
    [Fact]
    public void ProfileCannotExecuteServerHtmlOrUnsafeLinks()
    {
        var html=ProfileMarkdown.Render("<script>alert(1)</script>\n\n[run](javascript:alert) [data](data:text/html,bad) [docs](https://example.test/?q=\"onclick)\n\n![remote](https://example.test/tracker.png)");
        Assert.DoesNotContain("<script",html);Assert.DoesNotContain("<img",html);
        Assert.DoesNotContain("href=\"javascript:",html);Assert.DoesNotContain("href=\"data:",html);
        Assert.Contains("&lt;script&gt;",html);Assert.Contains("&quot;onclick",html);
        Assert.Contains("rel=\"noopener noreferrer\"",html);
    }
}
