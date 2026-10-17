"""Exact, full-history quantity summaries for a presentation-only chart."""
from decimal import Decimal,localcontext,Inexact
from .reconstruction import canonical


def movement_chart(items):
    points=[]
    with localcontext() as context:
        context.prec=512;context.traps[Inexact]=True
        for item in items:
            if not points or points[-1]['effectiveAt']!=item['effectiveAt']:
                points.append(dict(effectiveAt=item['effectiveAt'],buyQuantity=Decimal(0),sellQuantity=Decimal(0),
                    runningQuantity=item['runningQuantity'],tradeCount=0,splitQuantity=Decimal(0),splitRatios=[]))
            point=points[-1];quantity=Decimal(item['quantity'])
            if item['source']=='BOOKED_TRADE':
                point['buyQuantity' if quantity>0 else 'sellQuantity']+=quantity
                point['tradeCount']+=1
            else:
                point['splitQuantity']+=quantity
                if item.get('ratio') is not None:point['splitRatios'].append(item['ratio'])
            point['runningQuantity']=item['runningQuantity']
    return canonical(points)
