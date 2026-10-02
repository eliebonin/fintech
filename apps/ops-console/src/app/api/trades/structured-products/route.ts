import type {NextRequest} from 'next/server';
import {productWrite} from '@/lib/product-booking-bff';
export const dynamic='force-dynamic';
export function POST(request:NextRequest){return productWrite(request,'structured-products');}
