export const fundOnboardingStages = [
  { key: "FUND", title: "Fund vehicle", tradable: false },
  { key: "SHARE_CLASS", title: "Share class", tradable: true },
  { key: "LISTING", title: "Venue listing", tradable: true },
] as const;

export function validateFundDraft(value: { canonicalName: string; domicileCountry: string }): { canonicalName?: string; domicileCountry?: string } {
  return {
    ...(value.canonicalName.trim() ? {} : { canonicalName: "Enter the official fund or sub-fund name." }),
    ...(value.domicileCountry ? {} : { domicileCountry: "Select the fund domicile." }),
  };
}
