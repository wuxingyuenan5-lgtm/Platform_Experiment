# Indicator source attribution

The pure TypeScript indicator adaptations are migrated from the owner-supplied 澜序 multi-timeframe monitor archive, source revision `3399f41cd961b37023997cf180e8a2d2ccfec806`.

- `01_Pulu_Moving_Averages.pine`: Pulu\_, Pulu Moving Averages, Pine v5, MPL-2.0. The application retains the supplied default EMA periods 12/144/169/288/338/576/676.
- `02_Zero_Lag_MA_Trend_Levels_ChartPrime.pine`: ChartPrime, Zero Lag MA Trend Levels, Pine v5, MPL-2.0. The application retains the supplied EMA15 correction and ATR200 trend levels.
- `kalman.ts`: BackQuant adaptations; the source comments preserve the original indicator URLs and MPL notice.

Original Pine files are retained verbatim for attribution and inspection. The application's buffered and confirmed primary direction is defined by `rules.ts`; matching the supplied JavaScript does not establish independent parity with every TradingView configuration or a validated investment strategy.

Mozilla Public License 2.0: https://mozilla.org/MPL/2.0/
