# Azure News Processing Pipeline - Cost-Conscious Implementation PRD

## 1. Executive Summary

**Project**: Lean, serverless news processing pipeline on Azure  
**Objective**: Process RSS feeds via Miniflux webhooks, generate enterprise-grade metadata with strict cost controls  
**Timeline**: 6-8 weeks for MVP  
**Cost Target**: **<$500/month for 50K articles/day** (HARD CAP)  
**Strategy**: CPU-first architecture with selective Azure OpenAI enrichment (≤5% of articles)

## 2. Cost-First Design Principles

**Stage-A Dominance (90-95% of articles):**
- Comprehensive CPU-based metadata extraction
- Enterprise schema compliance with default values for missing fields
- No Azure OpenAI costs for routine content

**Stage-B Scarcity (≤5% of articles):**
- Azure OpenAI enrichment only for highest-value content
- Profile-based processing (Full/Medium/Light)
- Hard daily budget caps with automatic fallback

**Volume Reduction:**
- 20-30% deduplication before any processing
- Aggressive near-duplicate detection
- Wire service and PR content filtering

**Resource Optimization:**
- Scale-to-zero everywhere
- Cached entity linking and embeddings
- Lifecycle management for data storage

## 3. Technical Architecture

### 3.1 High-Level Data Flow
```
Miniflux → Azure Function (Webhook) → Storage Queue → Container Apps (CPU) → Router → 
├─ 90-95% → PostgreSQL (Stage-A + defaults)
└─ ≤5% → Azure OpenAI → Schema Completion → PostgreSQL
```

### 3.2 Azure Services Stack (Cost-Optimized)
- **Azure Functions (Consumption)**: Webhook ingestion + Public APIs
- **Storage Queues**: Message passing with DLQ support  
- **Container Apps (Consumption)**: CPU-only ML processing with aggressive autoscaling
- **Azure OpenAI**: gpt-4o-mini only (no gpt-4o at MVP)
- **PostgreSQL Flexible (B1ms)**: Burstable instance with lifecycle management
- **ADLS Gen2 (Cool)**: Archive storage for older content
- **Key Vault + Managed Identity**: Secure credential management

### 3.3 Processing Stages

**Stage-A (CPU-Only, 100% Coverage)**
- **Basic metadata**: URL, title, publisher, word count, language detection
- **Named Entity Recognition**: spaCy with cached Wikidata linking
- **Classification**: Category, beats, keywords (YAKE + rule-based)
- **Sentiment/tone**: DistilBERT ONNX INT8 multi-label classification
- **Extractive summarization**: TextRank/LSA for abstract + TLDR
- **Readability scoring**: Flesch-Kincaid + complexity analysis
- **Novelty detection**: pgvector similarity against recent articles
- **Basic bias detection**: Publisher priors + lexical analysis
- **Schema completion**: Fill missing editorial fields with null/default values

**Stage-B (Azure OpenAI, ≤5% Coverage)**
- **Profile-based processing**:
  - **Full Profile** (~2-3%): Complete editorial analysis, fact-checking, risk assessment
  - **Medium Profile** (~2%): Angles + pitch generation only
  - **Light Profile**: Stage-A defaults (fallback when budget exhausted)

**Routing Logic (Cost-Capped)**
```python
stage_a_result = process_stage_a(article)

# Early exits for cost control
if is_near_dup(article) or is_wire_copy(article) or daily_budget_exhausted():
    return complete_schema_with_defaults(stage_a_result)

# Priority-based Stage-B selection
priority_score = calculate_priority(novelty, desk_assignment, content_type)

if priority_score >= FULL_PROFILE_THRESHOLD and within_budget("full"):
    return process_full_profile(article, stage_a_result)
elif priority_score >= MEDIUM_PROFILE_THRESHOLD and within_budget("medium"):
    return process_medium_profile(article, stage_a_result)
else:
    return complete_schema_with_defaults(stage_a_result)
```

## 4. Data Models

### 4.1 Enterprise Schema with Profiles

**Stage-A Fields (Always Populated):**
```json
{
  "metadata": {
    "article": { /* complete */ },
    "classification": {
      "category": "...", "beats": [...], "keywords": [...],
      "sentiment": {...}, "tone": [...],
      "bias": { "label": "center", "score": 0.0, "method": "heuristic" }
    },
    "summary": { "abstract": "...", "tldr": "..." },
    "entities": { /* spaCy + cached Wikidata */ },
    "quality": { "readability": 65.2, "overall_confidence": 0.75 },
    "provenance": { "pipeline_version": "...", "models": [...] }
  }
}
```

**Stage-B Enrichment (Profile-Dependent):**
```json
{
  "editorial": {
    "profile": "full|medium|light",
    "newsworthiness": { /* full profile only */ },
    "fact_check": { /* full profile only */ },
    "angles": [...], /* medium+ profiles */
    "impact": { /* full profile only */ },
    "risks": { /* full profile only */ },
    "pitch": { /* medium+ profiles */ }
  },
  "context": { /* full profile only */ }
}
```

### 4.2 Profile Definitions

**Full Profile (2-3% of articles):**
- Frontpage/investigative content
- Breaking news with high impact
- Complete editorial analysis including fact-checking, risk assessment, context enrichment

**Medium Profile (2% of articles):**
- Significant stories requiring editorial angles
- Pitch generation without full risk analysis
- Streamlined processing for cost efficiency

**Light Profile (95% of articles):**
- Stage-A processing only
- Schema completed with default/null values for editorial fields
- Quality flagged as "basic" in provenance

## 5. Cost Model (Revised)

### 5.1 Projected Monthly Costs (50K articles/day)

| Component | Target Cost | Optimization Strategy |
|-----------|-------------|----------------------|
| **Azure Functions** | $45 | Efficient code, connection pooling |
| **Container Apps (Stage-A)** | $85 | CPU-only, aggressive scale-to-zero |
| **PostgreSQL Flexible (B1ms)** | $65 | Burstable, 30-day retention |
| **Storage & Queues** | $25 | Lifecycle policies, compression |
| **Azure OpenAI (gpt-4o-mini)** | $120 | ≤1,500 calls/day, 300-token outputs |
| **External APIs** | $25 | Cached Wikidata, rate-limited |
| **ADLS Gen2 (Cool/Archive)** | $35 | Automated lifecycle management |
| **Monitoring & Misc** | $40 | Basic Application Insights |
| **Total** | **$440/month** | **10% buffer → $485/month** |

### 5.2 Cost Controls (Enforced in Code)

**Hard Limits:**
- Maximum 1,500 Azure OpenAI calls per day
- Automatic fallback to Stage-A when budget exhausted
- Daily cost alerts at 80% and 95% of budget

**Optimization Strategies:**
- Deduplication reduces processing volume by 25%
- Cached entity linking (90% hit rate target)
- Abstract-only prompts (200-300 tokens vs 2000+ for full text)
- Aggressive scale-to-zero (Container Apps idle within 30 seconds)

## 6. API Specification (Profile-Aware)

### 6.1 Core Endpoints

**Articles with Profile Indication**
```
GET /api/article/{id}
→ Returns: Article + metadata with "profile" field indicating enrichment level

GET /api/article?profile=full|medium|light&cursor=&limit=&...
→ Returns: Filtered articles by processing profile
```

**Editorial Content (Profile-Dependent)**
```
GET /api/pitch/{article_id}
→ Returns: Pitch if available (medium+ profiles), 404 for light profile

GET /api/editorial/{article_id}
→ Returns: Full editorial analysis (full profile only), limited data for others
```

**Processing Status**
```
GET /api/status/budget
→ Returns: Daily AOAI usage, remaining budget, profile distribution

GET /api/status/profiles
→ Returns: { "full": 145, "medium": 892, "light": 47630, "total": 48667 }
```

### 6.2 Response Structure with Profiles

```json
{
  "id": "...",
  "metadata": {
    "processing": {
      "profile": "medium",
      "stage_a_confidence": 0.85,
      "editorial_confidence": 0.78,
      "cost_tier": "enhanced"
    },
    "editorial": {
      "angles": [...],
      "pitch": {...},
      "fact_check": null,
      "risks": null,
      "newsworthiness": null
    }
  }
}
```

## 7. Implementation Plan (Cost-Conscious)

### 7.1 Phase 1: Foundation (Week 1-2)
**Focus**: Basic infrastructure with cost monitoring
- [ ] Azure resource provisioning with cost alerts
- [ ] PostgreSQL schema optimized for retention policies
- [ ] Azure Functions with efficient connection management
- [ ] Storage Queue processing with batching
- [ ] Cost tracking dashboard implementation

### 7.2 Phase 2: Stage-A Optimization (Week 2-4)
**Focus**: CPU-efficient processing for 100% coverage
- [ ] Optimized spaCy NER pipeline (speed over accuracy)
- [ ] ONNX INT8 sentiment models with batch processing
- [ ] Cached entity linking service (Redis/memory cache)
- [ ] Extractive summarization (TextRank, no neural models)
- [ ] Rule-based classification for categories/beats
- [ ] Deduplication pipeline (URL + content hash + MinHash)

### 7.3 Phase 3: Selective Stage-B (Week 4-6)
**Focus**: Profile-based Azure OpenAI integration
- [ ] gpt-4o-mini deployment (no gpt-4o initially)
- [ ] Profile-based routing with budget enforcement
- [ ] Structured outputs for each profile type
- [ ] Cost tracking per profile and per day
- [ ] Automatic fallback mechanisms

### 7.4 Phase 4: Optimization & Monitoring (Week 6-8)
**Focus**: Cost validation and performance tuning
- [ ] Cost monitoring with automated alerts
- [ ] Performance optimization for Container Apps
- [ ] Cache hit rate optimization for entity linking
- [ ] Profile distribution analysis and tuning
- [ ] Golden-set evaluation for quality assurance

## 8. Cost Control Mechanisms

### 8.1 Automated Budget Management

```python
class BudgetManager:
    def __init__(self):
        self.daily_limits = {
            "full_profile": 75,      # ~$4.50/day
            "medium_profile": 125,   # ~$3.75/day  
            "total_calls": 1500,     # Hard cap
            "daily_budget": 16.00    # $480/month / 30 days
        }
    
    def can_process(self, profile_type):
        return (
            self.get_daily_usage(profile_type) < self.daily_limits[profile_type] and
            self.get_total_daily_usage() < self.daily_limits["total_calls"] and
            self.get_daily_cost() < self.daily_limits["daily_budget"]
        )
```

### 8.2 Performance Optimizations

**Container Apps Scaling:**
- Minimum replicas: 0 (scale-to-zero)
- Maximum replicas: 20
- Scale rule: Queue length > 100 messages
- Cool-down period: 30 seconds

**Database Optimization:**
- Connection pooling (pgbouncer)
- Read replicas for API queries
- Automatic index maintenance
- 30-day data retention with archive to ADLS

**Caching Strategy:**
- Entity linking cache: 48-hour TTL
- Embeddings cache: 7-day TTL
- Near-duplicate signatures: 30-day TTL

## 9. Quality Assurance with Cost Constraints

### 9.1 Adjusted Success Metrics

**Cost Metrics (Primary):**
- Monthly cost ≤ $500 (hard requirement)
- Daily Azure OpenAI usage ≤ 1,500 calls
- Cost per article ≤ $0.01 average

**Quality Metrics (Balanced):**
- Stage-A schema completion: 100%
- NER F1 score: >0.80 (reduced from 0.85 for speed)
- Extractive summary ROUGE: >0.55 (acceptable for speed)
- Editorial pitch approval: >75% (for medium+ profiles only)

**Performance Metrics:**
- 95% of articles processed within 60 seconds
- API response time <300ms for simple queries
- 99.5% uptime for critical endpoints

### 9.2 Quality vs Cost Trade-offs

**Accepted Limitations:**
- Not all articles receive full editorial analysis
- Entity linking may have lower precision due to caching
- Basic bias detection for most content
- Limited context enrichment at MVP

**Quality Safeguards:**
- High-priority content (frontpage, breaking) gets full treatment
- Golden-set evaluation on representative sample
- Editorial feedback loop for profile threshold tuning
- Gradual enhancement path as budget allows

## 10. Risk Mitigation

### 10.1 Cost Overrun Prevention

**Technical Safeguards:**
- Hard-coded daily limits in routing logic
- Real-time cost tracking with automatic shutoff
- Circuit breakers for external API calls
- Queue depth limits to prevent runaway scaling

**Operational Controls:**
- Daily cost review and alert system
- Weekly budget vs actual analysis
- Monthly profile distribution optimization
- Quarterly cost model validation

### 10.2 Quality Degradation Monitoring

**Automated Checks:**
- Schema validation failure rate monitoring
- Entity linking accuracy spot checks
- Editorial feedback score tracking
- Profile distribution analysis

**Manual Reviews:**
- Weekly sample review by editorial team
- Monthly golden-set evaluation
- Quarterly model performance assessment
- Semi-annual cost-benefit analysis

## 11. Success Criteria & Go-Live

### 11.1 Cost Benchmarks (Primary)
- [ ] 30-day average cost ≤ $480/month
- [ ] Peak daily cost ≤ $20
- [ ] Cost per article ≤ $0.012 (including infrastructure)
- [ ] Zero cost overrun incidents

### 11.2 Quality Benchmarks (Secondary)
- [ ] 100% Stage-A schema compliance
- [ ] >75% editorial satisfaction with medium+ profiles
- [ ] >80% accuracy for cached entity linking
- [ ] <5% schema validation failures

### 11.3 Performance Benchmarks
- [ ] Process 50K articles/day consistently
- [ ] 95% processed within 60 seconds
- [ ] API availability >99.5%
- [ ] Container Apps scale-to-zero within 2 minutes of idle

## 12. Post-Launch Optimization

### 12.1 Phase 2 Enhancements (Month 2-3)
- **Budget scaling**: Evaluate increasing Azure OpenAI usage based on ROI
- **Profile tuning**: Optimize thresholds based on editorial feedback
- **Caching improvements**: Advanced entity disambiguation with better caching
- **Performance optimization**: Fine-tune Container Apps scaling parameters

### 12.2 Phase 3 Growth (Month 4-6)
- **Enhanced profiles**: Add specialized profiles for different content types
- **Advanced bias detection**: Upgrade from heuristic to ML-based detection
- **Context enrichment**: Add timeline generation for high-priority articles
- **Multi-language expansion**: Add support for non-English content

## 13. Appendix

### 13.1 Cost Calculation Details

**Azure OpenAI Pricing (gpt-4o-mini):**
- Input tokens: $0.00015 per 1K tokens
- Output tokens: $0.00060 per 1K tokens
- Average call: 300 input + 300 output = $0.27
- Daily budget: 1,500 calls × $0.27 = $405/month

**Container Apps Consumption:**
- Per-second billing, scale-to-zero
- Estimated 45 minutes active time per day
- B-series CPU: $0.180/hour × 0.75 hours × 30 days = $4.05/month per replica
- Average 3 replicas = $85/month

### 13.2 Profile Selection Algorithm

```python
def determine_profile(article, stage_a_metadata):
    novelty = stage_a_metadata['novelty_score']
    desk = article['classification']['desk']
    content_type = article['classification']['content_type']
    
    # Full profile criteria
    if (desk in ['frontpage', 'investigations'] or 
        content_type == 'breaking' or
        (novelty > 0.85 and desk in ['politics', 'economics'])):
        return 'full'
    
    # Medium profile criteria  
    elif (novelty > 0.65 or 
          desk in ['business', 'technology'] or
          content_type in ['analysis', 'exclusive']):
        return 'medium'
    
    # Light profile (default)
    else:
        return 'light'
```

---

**Document Version**: 2.0 (Cost-Conscious)  
**Cost Target**: <$500/month  
**Processing Coverage**: 100% Stage-A, ≤5% Stage-B  
**Last Updated**: August 21, 2025