// UserStringDump — walks the #US (user-string) heap of a .NET assembly and
// emits every literal in source order with its heap offset. The #US heap is
// untouched by ConfuserEx method-body tampering (which only patches the IL
// stream that REFERENCES these strings via ldstr opcodes), so we recover
// 100% of string constants even when method bodies are unreadable.
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Text.Json;
using System.Text.Json.Serialization;

if (args.Length < 1)
{
    Console.Error.WriteLine("Usage: UserStringDump <assembly.dll> [<output.json>]");
    return 2;
}

string path = args[0];
string outPath = args.Length > 1 ? args[1] : Path.ChangeExtension(path, ".userstrings.json");

using var stream = File.OpenRead(path);
using var pe = new PEReader(stream);
var reader = pe.GetMetadataReader();

var entries = new List<object>();
// Walk the #US heap by repeated GetNextHandle on a UserStringHandle.
// Starting from offset 0 (the always-empty entry) and calling
// reader.GetNextHandle iteratively yields every present user string.
int heapSize = reader.GetHeapSize(HeapIndex.UserString);
UserStringHandle cursor = MetadataTokens.UserStringHandle(0);
while (true)
{
    cursor = reader.GetNextHandle(cursor);
    if (cursor.IsNil) break;
    int offset = MetadataTokens.GetHeapOffset(cursor);
    if (offset <= 0 || offset >= heapSize) break;
    string s = reader.GetUserString(cursor);
    if (s.Length == 0) continue;
    entries.Add(new {
        offset = offset,
        token = $"0x{(0x70_00_00_00 | offset):X8}",   // ldstr token form
        length = s.Length,
        value = s,
    });
}

var doc = new {
    source = Path.GetFileName(path),
    heap = "#US",
    note = "Every JWT-relevant or SQL/config literal referenced anywhere in the assembly's IL appears in this heap, even if the IL stream itself is obfuscated.",
    count = entries.Count,
    strings = entries,
};

var opts = new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping };
File.WriteAllText(outPath, JsonSerializer.Serialize(doc, opts));
Console.WriteLine($"Wrote {entries.Count} user strings → {outPath}");
return 0;
