import {InterestOpsPage,type InterestSearch} from '@/features/valuation/interest-ops-page';
export const dynamic='force-dynamic';
export default function InterestPage({searchParams}:{searchParams:InterestSearch}){return <InterestOpsPage stage="DAILY" searchParams={searchParams}/>;}
