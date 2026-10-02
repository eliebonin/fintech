import {NextRequest} from 'next/server';
import {productWrite} from '@/lib/product-booking-bff';
export async function POST(request:NextRequest){return productWrite(request,'bonds');}
