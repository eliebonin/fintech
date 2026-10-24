import type {NextRequest} from 'next/server';
import {productWrite} from '@/lib/product-booking-bff';
export function POST(request:NextRequest){return productWrite(request,'amcs');}
