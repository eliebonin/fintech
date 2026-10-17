import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it,vi} from 'vitest';
import {PublicationAction} from './publication-action';
it('offers a visible publication action for an independent reviewer without submitting anything',()=>{
 const publish=vi.fn();const html=renderToStaticMarkup(<PublicationAction status="STAGED" stagedBy="maker" actorId="reviewer" canReview busy={false} onPublish={publish}/>);
 expect(html).toContain('Publish valuation');expect(html).toContain('aria-expanded="false"');expect(publish).not.toHaveBeenCalled();
});
it('disables publication for the maker and explains independent review',()=>{
 const html=renderToStaticMarkup(<PublicationAction status="STAGED" stagedBy="maker" actorId="maker" canReview busy={false} onPublish={()=>{}}/>);
 expect(html).toContain('disabled');expect(html).toContain('independent reviewer');
});
it.each(['PUBLISHED','SUPERSEDED','CANCELLED'])('does not offer a mutation for %s evidence',status=>{
 const html=renderToStaticMarkup(<PublicationAction status={status} stagedBy="maker" actorId="reviewer" canReview busy={false} onPublish={()=>{}}/>);
 expect(html).not.toContain('<button');expect(html).not.toContain('<form');
});
it('does not offer publication without review authority',()=>{
 const html=renderToStaticMarkup(<PublicationAction status="STAGED" stagedBy="maker" actorId="viewer" canReview={false} busy={false} onPublish={()=>{}}/>);
 expect(html).not.toContain('<button');expect(html).toContain('review permission');
});
it('offers an explicitly labelled self-publication only when authorised',()=>{
 const html=renderToStaticMarkup(<PublicationAction status="STAGED" stagedBy="maker" actorId="maker" canReview canSelfPublish requiresSelfReview busy={false} onPublish={()=>{}}/>);
 expect(html).toContain('Publish without independent review');expect(html).not.toContain('disabled');
});
it('blocks even authorised self-publication when ledger inputs changed',()=>{
 const html=renderToStaticMarkup(<PublicationAction status="STAGED" stagedBy="maker" actorId="maker" canReview canSelfPublish requiresSelfReview sourceHealthStatus="REASSESSMENT_REQUIRED" busy={false} onPublish={()=>{}}/>);
 expect(html).toContain('disabled');expect(html).toContain('Recalculate');
});
