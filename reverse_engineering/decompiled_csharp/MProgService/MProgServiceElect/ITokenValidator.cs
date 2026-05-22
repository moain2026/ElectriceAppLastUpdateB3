using MProgService.models;

namespace MProgServiceElect;

public interface ITokenValidator
{
	Token Token { get; set; }

	bool IsValid(string token);
}
