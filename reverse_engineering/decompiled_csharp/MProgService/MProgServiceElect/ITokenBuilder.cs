using MProgService.models;

namespace MProgServiceElect;

internal interface ITokenBuilder
{
	string Build(Credentials creds);
}
