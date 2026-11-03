import {InterestOpsPage,type InterestSearch} from '@/features/valuation/interest-ops-page';
export const dynamic='force-dynamic';
export default function BalanceExplorerPage({searchParams}:{searchParams:InterestSearch}){return <InterestOpsPage stage="EXPLORE" searchParams={searchParams}/>;}
