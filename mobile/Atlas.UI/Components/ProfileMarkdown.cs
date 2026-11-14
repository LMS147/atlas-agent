using System.Net;
using System.Text;
using System.Text.RegularExpressions;

namespace Atlas.UI.Components;

/// <summary>Read-only Markdown subset. Source HTML is always encoded, never executed.
/// Images remain descriptive text; links are restricted to HTTP(S).</summary>
public static class ProfileMarkdown
{
    public static string Render(string source)
    {
        var output = new StringBuilder();
        var paragraph = new List<string>();
        string? list = null;
        bool code = false;
        void Flush() { if (paragraph.Count > 0) { output.Append("<p>").Append(Inline(string.Join("\n", paragraph))).Append("</p>"); paragraph.Clear(); } }
        void CloseList() { if (list is not null) { output.Append("</").Append(list).Append('>'); list = null; } }
        foreach (var line in source.Replace("\r\n", "\n").Split('\n'))
        {
            if (line.TrimStart().StartsWith("```", StringComparison.Ordinal))
            {
                Flush(); CloseList(); output.Append(code ? "</code></pre>" : "<pre><code>"); code = !code; continue;
            }
            if (code) { output.Append(WebUtility.HtmlEncode(line)).Append('\n'); continue; }
            if (string.IsNullOrWhiteSpace(line)) { Flush(); CloseList(); continue; }
            var heading = Regex.Match(line, @"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$");
            if (heading.Success) { Flush(); CloseList(); var level=heading.Groups[1].Length; output.Append($"<h{level}>").Append(Inline(heading.Groups[2].Value)).Append($"</h{level}>"); continue; }
            var item = Regex.Match(line, @"^\s*(?:([-+*])|\d+[.)])\s+(.+)$");
            if (item.Success) { Flush(); var kind=item.Groups[1].Success?"ul":"ol"; if(list!=kind){CloseList();output.Append('<').Append(kind).Append('>');list=kind;} output.Append("<li>").Append(Inline(item.Groups[2].Value)).Append("</li>"); continue; }
            CloseList();
            if (Regex.IsMatch(line.Trim(), @"^(---+|\*\*\*+|___+)$")) { Flush(); output.Append("<hr>"); continue; }
            if(line.StartsWith("> ",StringComparison.Ordinal)){Flush();output.Append("<blockquote>").Append(Inline(line[2..])).Append("</blockquote>");continue;}
            paragraph.Add(line);
        }
        Flush(); CloseList(); if(code)output.Append("</code></pre>");
        return output.ToString();
    }

    private static string Inline(string text)
    {
        // Tokenize before encoding, so generated markup never becomes input to another rule.
        var result=new StringBuilder();
        var tokens=Regex.Matches(text,@"(`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|\[[^\]\n]+\]\([^\s)]+\))");
        var offset=0;
        foreach(Match token in tokens)
        {
            result.Append(WebUtility.HtmlEncode(text[offset..token.Index]));
            var value=token.Value;
            if(value[0]=='`')result.Append("<code>").Append(WebUtility.HtmlEncode(value[1..^1])).Append("</code>");
            else if(value.StartsWith("**")||value.StartsWith("__"))result.Append("<strong>").Append(WebUtility.HtmlEncode(value[2..^2])).Append("</strong>");
            else if(value[0]=='*')result.Append("<em>").Append(WebUtility.HtmlEncode(value[1..^1])).Append("</em>");
            else
            {
                var split=value.IndexOf("](",StringComparison.Ordinal);var label=value[1..split];var url=value[(split+2)..^1];
                if(Uri.TryCreate(url,UriKind.Absolute,out var uri)&&uri.Scheme is "https" or "http")result.Append("<a rel=\"noopener noreferrer\" href=\"").Append(WebUtility.HtmlEncode(url)).Append("\">").Append(WebUtility.HtmlEncode(label)).Append("</a>");
                else result.Append(WebUtility.HtmlEncode(value));
            }
            offset=token.Index+token.Length;
        }
        return result.Append(WebUtility.HtmlEncode(text[offset..])).ToString();
    }
}
