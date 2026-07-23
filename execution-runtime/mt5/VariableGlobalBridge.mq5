#property strict
#property version   "1.00"

input string BridgeSymbol = "XAUUSD+";
input string BridgeFileName = "variable_global_mt5_bridge.json";
input int PublishSeconds = 2;

int OnInit()
{
   EventSetTimer(MathMax(1, PublishSeconds));
   PublishSnapshot();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   PublishSnapshot();
}

void PublishSnapshot()
{
   MqlTick tick;
   if(!SymbolInfoTick(BridgeSymbol, tick))
   {
      return;
   }

   string json = "{";
   json += "\"symbol\":\"" + JsonEscape(BridgeSymbol) + "\",";
   json += "\"bid\":" + DoubleToString(tick.bid, _Digits) + ",";
   json += "\"ask\":" + DoubleToString(tick.ask, _Digits) + ",";
   json += "\"last\":" + DoubleToString(tick.last, _Digits) + ",";
   json += "\"swapLong\":" + DoubleToString(SymbolInfoDouble(BridgeSymbol, SYMBOL_SWAP_LONG), 4) + ",";
   json += "\"swapShort\":" + DoubleToString(SymbolInfoDouble(BridgeSymbol, SYMBOL_SWAP_SHORT), 4) + ",";
   json += "\"time\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\",";
   json += "\"positions\":[";

   bool first = true;
   int total = PositionsTotal();
   for(int index = 0; index < total; index++)
   {
      ulong ticket = PositionGetTicket(index);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
      {
         continue;
      }

      string symbol = PositionGetString(POSITION_SYMBOL);
      if(symbol != BridgeSymbol)
      {
         continue;
      }

      if(!first)
      {
         json += ",";
      }
      first = false;

      long type = PositionGetInteger(POSITION_TYPE);
      string side = type == POSITION_TYPE_BUY ? "buy" : "sell";
      json += "{";
      json += "\"ticket\":" + IntegerToString((long)ticket) + ",";
      json += "\"symbol\":\"" + JsonEscape(symbol) + "\",";
      json += "\"side\":\"" + side + "\",";
      json += "\"volume\":" + DoubleToString(PositionGetDouble(POSITION_VOLUME), 2) + ",";
      json += "\"priceOpen\":" + DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), _Digits) + ",";
      json += "\"profit\":" + DoubleToString(PositionGetDouble(POSITION_PROFIT), 2);
      json += "}";
   }

   json += "]}";

   int handle = FileOpen(BridgeFileName, FILE_WRITE | FILE_TXT | FILE_COMMON | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("VariableGlobalBridge FileOpen failed: ", GetLastError());
      return;
   }
   FileWriteString(handle, json);
   FileClose(handle);
}

string JsonEscape(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   return value;
}
