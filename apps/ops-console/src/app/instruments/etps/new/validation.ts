export type EtpIdentityErrors = {
  canonicalName?: string;
  etpKind?: string;
  legalForm?: string;
  redemptionModel?: string;
};

export function validateEtpIdentity(canonicalName: string, etpKind: string, legalForm: string, redemptionModel: string): EtpIdentityErrors {
  return {
    ...(canonicalName.trim() ? {} : { canonicalName: "Enter the official ETP name." }),
    ...(etpKind ? {} : { etpKind: "Choose ETF, ETC, ETN, ETV, or ETI." }),
    ...(legalForm.trim() ? {} : { legalForm: "Choose the legal wrapper form." }),
    ...(redemptionModel.trim() ? {} : { redemptionModel: "Choose the redemption lifecycle." }),
  };
}
