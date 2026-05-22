using System;
using System.Diagnostics;
using System.Management;
using Microsoft.VisualBasic;
using Microsoft.VisualBasic.CompilerServices;

namespace License;

public class License
{
	[DebuggerNonUserCode]
	public License()
	{
	}

	public static object GetHDDSerialN(string DriveLetter = "C")
	{
		//IL_0038: Unknown result type (might be due to invalid IL or missing references)
		//IL_003e: Expected O, but got Unknown
		if ((Operators.CompareString(DriveLetter, "", false) == 0) | (Operators.CompareString(DriveLetter, (string)null, false) == 0))
		{
			DriveLetter = "C";
		}
		ManagementObject val = new ManagementObject("Win32_LogicalDisk.DeviceID=\"" + DriveLetter + ":\"");
		val.Get();
		return ((ManagementBaseObject)val)["VolumeSerialNumber"].ToString();
	}

	public static object PrimaryKey(string HDDSerial)
	{
		string text = "";
		string text2 = HDDSerial.ToUpper();
		checked
		{
			int num = text2.Length - 1;
			int num2 = 0;
			while (true)
			{
				int num3 = num2;
				int num4 = num;
				if (num3 > num4)
				{
					break;
				}
				char c = text2[num2];
				if (Versioned.IsNumeric((object)c))
				{
					char c2 = Strings.Chr(unchecked(checked(Conversion.Val(c) + num2 + 5) % 10) + 48);
					text += Conversions.ToString(c2);
				}
				else
				{
					char c2 = Strings.Chr((int)Math.Round((Conversion.Val((object)(Strings.Asc(c) - 65)) + (double)num2 + 3.0) % 27.0 + 65.0));
					text += Conversions.ToString(c2);
				}
				num2++;
			}
			return text;
		}
	}

	public static string GetFinalKey(string PrimaryKey)
	{
		string text = "";
		string text2 = PrimaryKey.ToUpper();
		checked
		{
			int num = text2.Length - 1;
			int num2 = 0;
			while (true)
			{
				int num3 = num2;
				int num4 = num;
				if (num3 > num4)
				{
					break;
				}
				char c = text2[num2];
				if (Versioned.IsNumeric((object)c))
				{
					char c2 = Strings.Chr(unchecked(checked(Conversion.Val(c) + num2 + 3) % 10) + 48);
					text += Conversions.ToString(c2);
				}
				else
				{
					char c2 = Strings.Chr((int)Math.Round((Conversion.Val((object)(Strings.Asc(c) - 65)) + (double)num2 + 5.0) % 27.0 + 65.0));
					text += Conversions.ToString(c2);
				}
				num2++;
			}
			return text;
		}
	}
}
