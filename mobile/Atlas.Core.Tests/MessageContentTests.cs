using Atlas.UI.Components;
using Microsoft.AspNetCore.Components;
using Microsoft.AspNetCore.Components.Web;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Atlas.Core.Tests;
public sealed class MessageContentTests
{
    [Fact]
    public async Task ModelHtmlRemainsEncodedIncludingInsideCodeBlocks()
    {
        using var services=new ServiceCollection().AddLogging().BuildServiceProvider();
        await using var renderer=new HtmlRenderer(services,services.GetRequiredService<ILoggerFactory>());
        var html=await renderer.Dispatcher.InvokeAsync(async()=>
        {
            var component=await renderer.RenderComponentAsync<MessageContent>(ParameterView.FromDictionary(new Dictionary<string,object?>{["Text"]="Hello <script>alert(1)</script>\n```html\n<img src=x onerror=alert(1)>\n```\nDone"}));
            return component.ToHtmlString();
        });
        Assert.DoesNotContain("<script>",html);
        Assert.DoesNotContain("<img",html);
        Assert.Contains("&lt;script&gt;",html);
        Assert.Contains("<pre><code>",html);
        Assert.Contains("Done",html);
    }
}
