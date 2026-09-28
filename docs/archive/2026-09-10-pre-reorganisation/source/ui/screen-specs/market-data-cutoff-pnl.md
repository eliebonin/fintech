# Market-data cutoff and P&L lab

The MVP includes a clearly labelled illustrative lab on the operations home
screen. It uses the synthetic GBP/USD cutoff fixture to make the selection and
P&L chain visible:

1. Select either the UK fund context (16:00 Europe/London, 15:00 UTC) or the
   US fund context (16:00 America/New_York, 20:00 UTC).
2. Show the local holding, quote factor, unit multiplier, previous and selected
   FX inputs, and the frozen information cut.
3. Show opening and closing reporting-currency values and a small P&L bridge for
   local-market and FX translation effects.
4. Keep the later post-cut print visible as retained history, but mark it as
   ineligible for the selected historic cutoff.

The displayed UK example is a USD cash balance translated into GBP using the
inverse `USD per GBP` quote. The US example is a GBP-denominated HSBC XLON
holding quoted in GBX, translated directly into USD. The decomposition uses
closing FX for the local-market effect and opening local value for the FX
effect; the two components sum to total P&L.

## Modelling findings exposed by the lab

- A P&L run needs an opening position/valuation input as well as a closing
  observation. Market-data observations alone are not enough.
- Quote factor and unit multiplier must be applied before currency conversion;
  the US example would be wrong if the GBX factor of 100 were ignored.
- The valuation cut must be persisted as both a named local-time cut and the
  resolved UTC information cutoff used by the run.
- The current MVP still needs a governed local-time-to-UTC/calendar resolver
  and an API endpoint that links the lab to persisted position and NAV input
  snapshots. The current lab is intentionally marked illustrative rather than
  presenting static values as a booked P&L run.
