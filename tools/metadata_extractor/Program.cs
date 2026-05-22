// =============================================================================
//  MetaExtract — pure metadata reader for obfuscated .NET assemblies.
//  Bypasses ConfuserEx control-flow tampering by reading ONLY metadata
//  tables (TypeDef, MethodDef, FieldDef, PropertyDef, CustomAttribute).
//  Does NOT touch method bodies (which are the obfuscated parts).
//
//  Output: JSON document with the full type/member surface of the assembly,
//          plus a flat list of resolved CustomAttribute blobs.
//
//  Usage:
//     dotnet run --project tools/metadata_extractor \
//                -- ../../binaries/MProgService.dll  > out.json
// =============================================================================
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace MetaExtract;

internal static class Program
{
    private static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.Error.WriteLine("usage: MetaExtract <assembly.dll>");
            return 2;
        }

        var path = args[0];
        if (!File.Exists(path))
        {
            Console.Error.WriteLine($"file not found: {path}");
            return 2;
        }

        using var fs = File.OpenRead(path);
        using var pe = new PEReader(fs);
        var mr = pe.GetMetadataReader();

        var dump = new AssemblyDump
        {
            File = Path.GetFileName(path),
            AssemblyName = mr.GetString(mr.GetAssemblyDefinition().Name),
            AssemblyVersion = mr.GetAssemblyDefinition().Version.ToString(),
            ModuleName = mr.GetString(mr.GetModuleDefinition().Name),
        };

        // External assembly references
        foreach (var arHandle in mr.AssemblyReferences)
        {
            var ar = mr.GetAssemblyReference(arHandle);
            dump.AssemblyReferences.Add($"{mr.GetString(ar.Name)} v{ar.Version}");
        }

        // Custom attributes at the assembly level (e.g. ConfusedByAttribute)
        foreach (var caH in mr.GetAssemblyDefinition().GetCustomAttributes())
        {
            dump.AssemblyAttributes.Add(DescribeCustomAttribute(mr, caH));
        }

        // Walk every TypeDef
        foreach (var tdH in mr.TypeDefinitions)
        {
            var td = mr.GetTypeDefinition(tdH);
            var typeName = mr.GetString(td.Name);
            var nsName   = mr.GetString(td.Namespace);
            // Skip <Module> + nested compiler-gen anonymous types
            if (typeName == "<Module>") continue;

            var typeInfo = new TypeInfo
            {
                Namespace = nsName,
                Name      = typeName,
                FullName  = string.IsNullOrEmpty(nsName) ? typeName : $"{nsName}.{typeName}",
                Attributes = td.Attributes.ToString(),
                IsInterface = td.Attributes.HasFlag(System.Reflection.TypeAttributes.Interface),
                IsAbstract  = td.Attributes.HasFlag(System.Reflection.TypeAttributes.Abstract),
                BaseType    = DescribeEntity(mr, td.BaseType),
            };

            // Interfaces implemented
            foreach (var ifaceH in td.GetInterfaceImplementations())
            {
                var iface = mr.GetInterfaceImplementation(ifaceH);
                typeInfo.Interfaces.Add(DescribeEntity(mr, iface.Interface));
            }

            // Type-level custom attributes (e.g. [ServiceContract], [DataContract])
            foreach (var caH in td.GetCustomAttributes())
            {
                typeInfo.Attributes_List.Add(DescribeCustomAttribute(mr, caH));
            }

            // Fields
            foreach (var fdH in td.GetFields())
            {
                var fd = mr.GetFieldDefinition(fdH);
                var fInfo = new FieldInfo
                {
                    Name = mr.GetString(fd.Name),
                    Signature = DecodeSignature(mr, fd.Signature, isField: true),
                    Attributes = fd.Attributes.ToString(),
                };
                foreach (var caH in fd.GetCustomAttributes())
                    fInfo.Attributes_List.Add(DescribeCustomAttribute(mr, caH));
                typeInfo.Fields.Add(fInfo);
            }

            // Properties
            foreach (var pdH in td.GetProperties())
            {
                var pd = mr.GetPropertyDefinition(pdH);
                var pInfo = new PropertyInfo
                {
                    Name = mr.GetString(pd.Name),
                    Signature = DecodeSignature(mr, pd.Signature, isField: false),
                    Attributes = pd.Attributes.ToString(),
                };
                foreach (var caH in pd.GetCustomAttributes())
                    pInfo.Attributes_List.Add(DescribeCustomAttribute(mr, caH));
                typeInfo.Properties.Add(pInfo);
            }

            // Methods (signature ONLY — NOT bodies, which are the obfuscated parts)
            foreach (var mdH in td.GetMethods())
            {
                var md = mr.GetMethodDefinition(mdH);
                var mInfo = new MethodInfo
                {
                    Name = mr.GetString(md.Name),
                    Signature = DecodeSignature(mr, md.Signature, isField: false),
                    Attributes = md.Attributes.ToString(),
                    ImplAttributes = md.ImplAttributes.ToString(),
                };
                foreach (var caH in md.GetCustomAttributes())
                    mInfo.Attributes_List.Add(DescribeCustomAttribute(mr, caH));

                // Parameter names + attributes (e.g. [WebInvoke] is on method not param,
                // but params hold [DataMember]).
                foreach (var pH in md.GetParameters())
                {
                    var p = mr.GetParameter(pH);
                    var pInfo = new ParamInfo
                    {
                        Name = mr.GetString(p.Name),
                        SequenceNumber = p.SequenceNumber,
                    };
                    foreach (var caH in p.GetCustomAttributes())
                        pInfo.Attributes_List.Add(DescribeCustomAttribute(mr, caH));
                    mInfo.Parameters.Add(pInfo);
                }

                typeInfo.Methods.Add(mInfo);
            }

            dump.Types.Add(typeInfo);
        }

        var json = JsonSerializer.Serialize(dump, new JsonSerializerOptions
        {
            WriteIndented = true,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingDefault,
        });
        Console.Out.Write(json);
        return 0;
    }

    // ----------------------------------------------------------------------
    //  Signature decoding (very compact — we just want a readable string).
    // ----------------------------------------------------------------------
    private static unsafe string DecodeSignature(MetadataReader mr, BlobHandle sigHandle, bool isField)
    {
        try
        {
            var bytes = mr.GetBlobBytes(sigHandle);
            fixed (byte* p = bytes)
            {
                var blob = new BlobReader(p, bytes.Length);
                var dec = new SignatureDecoder<string, object?>(
                    new PrimitiveTypeProvider(mr), mr, null);
                if (isField)
                {
                    return dec.DecodeFieldSignature(ref blob);
                }
                else
                {
                    var sig = dec.DecodeMethodSignature(ref blob);
                    var paramStr = string.Join(", ", sig.ParameterTypes);
                    return $"{sig.ReturnType} ({paramStr})";
                }
            }
        }
        catch (Exception ex)
        {
            return $"<decode-error: {ex.GetType().Name}>";
        }
    }

    // ----------------------------------------------------------------------
    //  Custom attribute → "Namespace.Type"+raw-blob-base64.
    //  We don't try to decode the *arguments* — for the obfuscated ones,
    //  the blob is itself encrypted and useless. We just record the type
    //  name and the raw bytes for offline inspection.
    // ----------------------------------------------------------------------
    private static CustomAttributeInfo DescribeCustomAttribute(MetadataReader mr, CustomAttributeHandle caH)
    {
        var ca = mr.GetCustomAttribute(caH);
        var ctor = DescribeEntity(mr, ca.Constructor);
        var blobBytes = mr.GetBlobBytes(ca.Value);
        return new CustomAttributeInfo
        {
            Ctor = ctor,
            BlobBase64 = Convert.ToBase64String(blobBytes),
            BlobLength = blobBytes.Length,
            // Best-effort string scan for readable UTF-8 substrings ≥ 4 chars.
            BlobStrings = ExtractReadableStrings(blobBytes),
        };
    }

    private static List<string> ExtractReadableStrings(byte[] blob)
    {
        var found = new List<string>();
        var sb = new StringBuilder();
        foreach (var b in blob)
        {
            if (b >= 0x20 && b < 0x7F) sb.Append((char)b);
            else
            {
                if (sb.Length >= 4) found.Add(sb.ToString());
                sb.Clear();
            }
        }
        if (sb.Length >= 4) found.Add(sb.ToString());
        return found;
    }

    // Best-effort textual description of any entity handle (method / type ref / spec).
    private static string DescribeEntity(MetadataReader mr, EntityHandle h)
    {
        if (h.IsNil) return "";
        try
        {
            switch (h.Kind)
            {
                case HandleKind.TypeDefinition:
                    var td = mr.GetTypeDefinition((TypeDefinitionHandle)h);
                    return $"{mr.GetString(td.Namespace)}.{mr.GetString(td.Name)}";
                case HandleKind.TypeReference:
                    var tr = mr.GetTypeReference((TypeReferenceHandle)h);
                    return $"{mr.GetString(tr.Namespace)}.{mr.GetString(tr.Name)}";
                case HandleKind.TypeSpecification:
                    return "<TypeSpec>";
                case HandleKind.MemberReference:
                    var mref = mr.GetMemberReference((MemberReferenceHandle)h);
                    return $"{DescribeEntity(mr, mref.Parent)}::{mr.GetString(mref.Name)}";
                case HandleKind.MethodDefinition:
                    var mdef = mr.GetMethodDefinition((MethodDefinitionHandle)h);
                    return mr.GetString(mdef.Name);
                default:
                    return $"<{h.Kind}>";
            }
        }
        catch
        {
            return "<err>";
        }
    }
}

// =============================================================================
//  Signature provider — minimal, just produces readable strings.
// =============================================================================
internal sealed class PrimitiveTypeProvider : ISignatureTypeProvider<string, object?>
{
    private readonly MetadataReader _mr;
    public PrimitiveTypeProvider(MetadataReader mr) => _mr = mr;

    public string GetPrimitiveType(PrimitiveTypeCode typeCode) => typeCode.ToString();
    public string GetTypeFromDefinition(MetadataReader reader, TypeDefinitionHandle handle, byte rawTypeKind)
    {
        var td = reader.GetTypeDefinition(handle);
        return $"{reader.GetString(td.Namespace)}.{reader.GetString(td.Name)}";
    }
    public string GetTypeFromReference(MetadataReader reader, TypeReferenceHandle handle, byte rawTypeKind)
    {
        var tr = reader.GetTypeReference(handle);
        return $"{reader.GetString(tr.Namespace)}.{reader.GetString(tr.Name)}";
    }
    public string GetTypeFromSpecification(MetadataReader reader, object? genericContext, TypeSpecificationHandle handle, byte rawTypeKind) => "<typespec>";

    public string GetSZArrayType(string elementType) => elementType + "[]";
    public string GetArrayType(string elementType, ArrayShape shape) => elementType + "[]";
    public string GetPointerType(string elementType) => elementType + "*";
    public string GetByReferenceType(string elementType) => elementType + "&";
    public string GetGenericMethodParameter(object? genericContext, int index) => "!!" + index;
    public string GetGenericTypeParameter(object? genericContext, int index) => "!" + index;
    public string GetGenericInstantiation(string genericType, System.Collections.Immutable.ImmutableArray<string> typeArguments)
        => $"{genericType}<{string.Join(",", typeArguments)}>";
    public string GetFunctionPointerType(MethodSignature<string> signature) => "<fnptr>";
    public string GetModifiedType(string modifier, string unmodifiedType, bool isRequired) => unmodifiedType;
    public string GetPinnedType(string elementType) => elementType + "^pinned";
    public string GetTypeFromHandle(MetadataReader reader, object? genericContext, EntityHandle handle) => "<?>";
}

// =============================================================================
//  DTOs that get serialized to JSON.
// =============================================================================
internal sealed class AssemblyDump
{
    public string File { get; set; } = "";
    public string AssemblyName { get; set; } = "";
    public string AssemblyVersion { get; set; } = "";
    public string ModuleName { get; set; } = "";
    public List<string> AssemblyReferences { get; set; } = new();
    public List<CustomAttributeInfo> AssemblyAttributes { get; set; } = new();
    public List<TypeInfo> Types { get; set; } = new();
}

internal sealed class TypeInfo
{
    public string Namespace { get; set; } = "";
    public string Name { get; set; } = "";
    public string FullName { get; set; } = "";
    public string Attributes { get; set; } = "";
    public bool IsInterface { get; set; }
    public bool IsAbstract { get; set; }
    public string BaseType { get; set; } = "";
    public List<string> Interfaces { get; set; } = new();
    [JsonPropertyName("CustomAttributes")]
    public List<CustomAttributeInfo> Attributes_List { get; set; } = new();
    public List<FieldInfo> Fields { get; set; } = new();
    public List<PropertyInfo> Properties { get; set; } = new();
    public List<MethodInfo> Methods { get; set; } = new();
}

internal sealed class FieldInfo
{
    public string Name { get; set; } = "";
    public string Signature { get; set; } = "";
    public string Attributes { get; set; } = "";
    [JsonPropertyName("CustomAttributes")]
    public List<CustomAttributeInfo> Attributes_List { get; set; } = new();
}

internal sealed class PropertyInfo
{
    public string Name { get; set; } = "";
    public string Signature { get; set; } = "";
    public string Attributes { get; set; } = "";
    [JsonPropertyName("CustomAttributes")]
    public List<CustomAttributeInfo> Attributes_List { get; set; } = new();
}

internal sealed class MethodInfo
{
    public string Name { get; set; } = "";
    public string Signature { get; set; } = "";
    public string Attributes { get; set; } = "";
    public string ImplAttributes { get; set; } = "";
    [JsonPropertyName("CustomAttributes")]
    public List<CustomAttributeInfo> Attributes_List { get; set; } = new();
    public List<ParamInfo> Parameters { get; set; } = new();
}

internal sealed class ParamInfo
{
    public string Name { get; set; } = "";
    public int SequenceNumber { get; set; }
    [JsonPropertyName("CustomAttributes")]
    public List<CustomAttributeInfo> Attributes_List { get; set; } = new();
}

internal sealed class CustomAttributeInfo
{
    public string Ctor { get; set; } = "";
    public int BlobLength { get; set; }
    public string BlobBase64 { get; set; } = "";
    public List<string> BlobStrings { get; set; } = new();
}
