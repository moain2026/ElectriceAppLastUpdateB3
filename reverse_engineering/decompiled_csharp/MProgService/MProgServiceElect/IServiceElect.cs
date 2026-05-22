using System.Collections.Generic;
using System.ServiceModel;
using System.ServiceModel.Web;
using MProgService.models;

namespace MProgServiceElect;

[ServiceContract]
public interface IServiceElect
{
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	string Authenticate(Credentials creds);

	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	string test();

	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	List<Accounts> GetListAccounts(string num, string m, string g, string p, string acctid, string appId);

	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	List<pGroup> GetListGroup(string no_mstlm, string appId);

	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	List<plocation> GetListPlaces(string nou, string type, string appId);

	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	List<RepBoxMoves> GetRepBoxMove(string sdate, string appId);

	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	List<RepBoxMovesDetals> GetRepBoxMoveDetails(string sdate, string num, string appId);

	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	List<RepBoxMovesDetals> GetRepExpenses(string sdate, string appId);

	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	List<UserPlaces> GetListUserPlaces(string num, string appId);

	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	List<ItemReading> GetListReadingCounter(string id, string isnull, string notblh, string nomstlm, string nogroup, string appId);

	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[FaultContract(typeof(ServiceFault))]
	ResultPost SaveReading(string num, string kh, string appId);

	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	List<Users> GetListUsers(string id, string appId);

	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	List<RepReading> GetRepReadingHeader(string type, string appId);

	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	List<RepBalanceDetails> GetRepBalanceDetailsByDate(string num, string sdate, string edate, string currency, string appId);

	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	List<RepBalanceHeader> GetRepBalanceHeader(string date, string currency, string num, string type, string appId);

	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	List<RepBondsHeader> GetRepBondsHeader(string num, string sdate, string edate, string currency, string appId);

	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	string GetBondRecieptRcordNext(string num, string appId);

	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	List<ItemBonds> GetListBonds(string num, string num_s, string sdate, string edate, string currency, string nou, string appId);

	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	ResultPost SaveBond(string num, string num_s, string nmstnd, double mden, string mdate, string notes, string notes_box, string currencyid, double dain, double price_trans, double equal, string notes2, string appId);

	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	ResultPost UpdateBond(string appId, string id, string num, string num_s, string nmstnd, double mden, string mdate, string notes, string notes_box, string currencyid, double dain, double price_trans, double equal, string notes2);

	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	ResultPost DeleteBond(string appId, string id);

	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	string GetBondPaymentRecordNext(string num, string appId);

	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	List<ItemBonds> GetListBondsPayment(string num, string num_s, string sdate, string edate, string currency, string appId);

	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	ResultPost SaveBondPayment(string num, string num_s, string nmstnd, double mden, string mdate, string notes, string notes_box, string currencyid, double dain, double price_trans, double equal, string notes2, string appId);

	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	ResultPost UpdateBondPayment(string appId, string id, string num, string num_s, string nmstnd, double mden, string mdate, string notes, string notes_box, string currencyid, double dain, double price_trans, double equal, string notes2);

	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	ResultPost DeleteBondPayment(string appId, string id);

	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	Users Login(string username, string password, string appId, string secureId);

	[FaultContract(typeof(ServiceFault))]
	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	List<AccountBalanceInfo> GetAccountBalanceInfo(string date, string accountid, string appId);

	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	string GetAccountBalance(string accountid, string currency, string appId);

	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[FaultContract(typeof(ServiceFault))]
	CompanyInfo GetCompanyInfo(string appId);

	[FaultContract(typeof(ServiceFault))]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	DataComp GetCompanyData();

	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[OperationContract]
	[FaultContract(typeof(ServiceFault))]
	ChangePasswordRespons ReSetPassword(string username, string password, string newpassword, string uId, string appId);

	[OperationContract]
	[WebInvoke(/*Could not decode attribute arguments.*/)]
	[FaultContract(typeof(ServiceFault))]
	string InsertMessage(string customerN, string phoneNo, string customerName, string ms1, string tg, string nos, string uId, string appId);
}
