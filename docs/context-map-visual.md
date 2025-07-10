# Visual Context Map

## Bounded Context Relationships

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   ZAMAZ DEBATE SYSTEM                                │
│                                                                                      │
│  ┌─────────────────────┐         ┌─────────────────────┐                           │
│  │   DEBATE CONTEXT    │◄────────│  EVOLUTION CONTEXT  │                           │
│  │   (Core Domain)     │  Evolution  │  (Generic Subdomain)│                        │
│  │                     │  Triggers   │                     │                        │
│  │ • DebateSession     │         │ • Evolution         │                           │
│  │ • Decision          │         │ • Improvement       │                           │
│  │ • Complexity        │         │ • History           │                           │
│  └──────────┬──────────┘         └──────────▲──────────┘                           │
│             │                                │                                      │
│             │ Decisions                      │ Performance                          │
│             │ Require                        │ Triggers                             │
│             │ Implementation                 │ Evolution                            │
│             │                                │                                      │
│  ┌──────────▼──────────┐         ┌──────────┴──────────┐                           │
│  │ IMPLEMENTATION      │         │ PERFORMANCE CONTEXT │                           │
│  │ CONTEXT             │         │ (Supporting Domain) │                           │
│  │ (Supporting Domain) │         │                     │                           │
│  │                     │         │ • Metric            │                           │
│  │ • Task              │         │ • Benchmark         │                           │
│  │ • PullRequest       │         │ • Optimization      │                           │
│  │ • Assignment        │         │                     │                           │
│  └──────────┬──────────┘         └─────────────────────┘                           │
│             │                                                                       │
│             │ Requests                                                             │
│             │ Testing                                                              │
│             │                                                                       │
│  ┌──────────▼──────────┐         ┌─────────────────────┐                           │
│  │  TESTING CONTEXT    │         │ AI INTEGRATION      │                           │
│  │ (Supporting Domain) │         │ CONTEXT             │                           │
│  │                     │         │ (Generic Subdomain) │                           │
│  │ • TestSuite         │◄────────│                     │                           │
│  │ • TestCase          │  Uses   │ • AIProvider        │                           │
│  │ • MockConfig        │  AI for  │ • Conversation      │                           │
│  │ • Coverage          │  Tests   │ • Cache             │                           │
│  └─────────────────────┘         └─────────────────────┘                           │
│                                             ▲                                       │
│                                             │ All contexts                          │
│                                             │ use AI services                       │
│                                             │                                       │
└─────────────────────────────────────────────┴───────────────────────────────────────┘

Legend:
  ◄──── : Upstream/Downstream relationship
  ──── : Partnership/Collaboration
```

## Integration Patterns Detail

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              INTEGRATION PATTERNS                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  SHARED KERNEL                           ANTICORRUPTION LAYER                       │
│  ┌───────────────┐                       ┌───────────────────┐                     │
│  │ Domain Events │                       │  AI Integration   │                     │
│  │ • EventBus    │                       │  ┌─────────────┐  │                     │
│  │ • DomainEvent │                       │  │ ACL         │  │                     │
│  │ • Handlers    │                       │  │ ┌─────────┐ │  │                     │
│  └───────┬───────┘                       │  │ │Provider │ │  │                     │
│          │                               │  │ │Adapter  │ │  │                     │
│    Used by all                           │  │ └─────────┘ │  │                     │
│    contexts                              │  └─────────────┘  │                     │
│                                          └───────────────────┘                     │
│                                                                                      │
│  OPEN HOST SERVICE                       PUBLISHED LANGUAGE                         │
│  ┌───────────────┐                       ┌───────────────────┐                     │
│  │Testing Context│                       │  Debate Context   │                     │
│  │  ┌─────────┐  │                       │  ┌─────────────┐  │                     │
│  │  │   API   │  │◄──────                │  │ Decision    │  │                     │
│  │  │ Service │  │       │               │  │ Types       │  │                     │
│  │  └─────────┘  │       │               │  │ • SIMPLE    │  │                     │
│  └───────────────┘       │               │  │ • COMPLEX   │  │                     │
│                          │               │  │ • EVOLUTION │  │                     │
│                    Other contexts        │  └─────────────┘  │                     │
│                    consume API           └───────────────────┘                     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Event Flow Sequences

```
DECISION TO IMPLEMENTATION FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Debate          Implementation      Testing         Performance
  │                  │                │                 │
  │ DecisionMade     │                │                 │
  ├─────────────────►│                │                 │
  │                  │                │                 │
  │                  │ TaskCreated    │                 │
  │                  ├───────────────►│                 │
  │                  │                │                 │
  │                  │                │ TestExecuted    │
  │                  │                ├────────────────►│
  │                  │                │                 │
  │                  │◄───────────────┤                 │
  │                  │ TestCompleted  │                 │
  │                  │                │                 │


PERFORMANCE TO EVOLUTION FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Performance     Evolution       Debate         Implementation
  │                │              │                 │
  │ Threshold      │              │                 │
  │ Exceeded       │              │                 │
  ├───────────────►│              │                 │
  │                │              │                 │
  │                │ Evolution    │                 │
  │                │ Triggered    │                 │
  │                ├─────────────►│                 │
  │                │              │                 │
  │                │              │ Decision        │
  │                │              │ Made           │
  │                │              ├────────────────►│
  │                │              │                 │
```

## Context Characteristics

```
┌────────────────┬─────────────┬──────────────┬─────────────┬──────────────┐
│    Context     │   Domain    │  Complexity  │ Change Rate │ Team Owner   │
├────────────────┼─────────────┼──────────────┼─────────────┼──────────────┤
│ Debate         │ Core        │ High         │ Low         │ Core Team    │
│ Implementation │ Supporting  │ Medium       │ Medium      │ DevOps       │
│ Testing        │ Supporting  │ Medium       │ Low         │ QA Team      │
│ Performance    │ Supporting  │ High         │ Medium      │ SRE Team     │
│ Evolution      │ Generic     │ High         │ High        │ Architecture │
│ AI Integration │ Generic     │ Low          │ High        │ Platform     │
└────────────────┴─────────────┴──────────────┴─────────────┴──────────────┘
```

## Communication Matrix

```
         │ Debate │ Impl. │ Test │ Perf │ Evol │ AI Int │
─────────┼────────┼───────┼──────┼──────┼──────┼────────┤
Debate   │   -    │  >>>  │  -   │  <   │  <<  │   >    │
Impl.    │   <    │   -   │ >>>  │  >   │  <   │   >    │
Test     │   -    │  <<   │  -   │  >>  │  <   │   >    │
Perf     │   >    │   <   │  <<  │  -   │ >>>  │   >    │
Evol     │  >>>   │  >>   │  >   │  <<  │  -   │   >    │
AI Int   │   <    │   <   │  <   │  <   │  <   │   -    │

Legend:
>>> : Heavy communication (many events/calls)
>>  : Moderate communication
>   : Light communication
<   : Receives communication
<<  : Receives moderate communication
<<< : Receives heavy communication
-   : No self-communication
```