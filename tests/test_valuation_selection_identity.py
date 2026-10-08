from copy import deepcopy

def test_source_and_calendar_change_reversions_evidence_but_information_time_alone_does_not():
    from valuation.storage import selection_identity
    row={'selected_value':'100','dataset_id':'dataset-a','pricing_evidence':{
        'pricingTargetUtc':'2026-10-01T15:00:00Z','informationCutoffUtc':'2026-10-02T00:00:00Z',
        'calendarEvidence':{'calendarId':'calendar-a','sealed':True,'versionNo':1}}}
    identity=selection_identity(row)
    later=deepcopy(row);later['pricing_evidence']['informationCutoffUtc']='2026-10-03T00:00:00Z'
    assert selection_identity(later)==identity
    calendar=deepcopy(row);calendar['pricing_evidence']['calendarEvidence']['calendarId']='calendar-b'
    assert selection_identity(calendar)!=identity
    dataset=deepcopy(row);dataset['dataset_id']='dataset-b'
    assert selection_identity(dataset)!=identity
