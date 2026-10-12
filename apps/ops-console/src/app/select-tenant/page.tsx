import { redirect } from 'next/navigation';

/** Keep old links without reviving the fixed demo-user selector. */
export default function SelectTenantPage() { redirect('/select-context'); }
