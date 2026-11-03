import {InterestOpsPage,type InterestSearch} from '@/features/valuation/interest-ops-page';
export const dynamic='force-dynamic';
export default function BalanceReviewPage({searchParams}:{searchParams:InterestSearch}){return <InterestOpsPage stage="BALANCE" searchParams={searchParams}/>;}
