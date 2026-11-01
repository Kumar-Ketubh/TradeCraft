# backend/seed_test_data.py
"""
Seeds comprehensive, realistic competitive intelligence test data for TradeCraft.
Provides competitors, sources, snapshots, unified diffs, changes, findings, and proposals
for the admin user to thoroughly test the AI pipeline, diff viewer, findings feed, and proposal engine.
"""

import os
import sys
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Ensure backend root is on sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(".env")

from app.db.database import create_db_engine
from app.models.user import User
from app.models.workspace import Workspace
from app.models.competitor import Competitor
from app.models.source import Source
from app.models.snapshot import Snapshot
from app.models.scan_run import ScanRun
from app.models.change import Change
from app.models.finding import IntelligenceFinding, EvidenceQuote, FindingCategory, VerificationStatus, ConfidenceLevel
from app.models.proposal import Proposal, ProposalStatus
from sqlalchemy.orm import sessionmaker

def seed_rich_test_data():
    engine = create_db_engine()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        admin = db.query(User).filter(User.email == "admin@tradecraft.com").first()
        if not admin:
            print("❌ Admin user not found! Please run seed_admin.py first.")
            return

        # Target the primary workspace
        ws = db.query(Workspace).filter(
            Workspace.user_id == admin.id,
            Workspace.name == "Admin Workspace"
        ).first()

        if not ws:
            ws = Workspace(
                name="Admin Workspace",
                user_id=admin.id,
                product_name="TradeCraft Suite",
                value_proposition="AI-powered competitive intelligence with automated verified evidence grounding and executive counter-proposals.",
                target_audience="B2B SaaS Product Managers, Competitive Intelligence Directors, and Enterprise Sales Strategy Teams.",
                pricing_summary="Starter free tier, $99/mo Pro tier, and $499/mo Enterprise tier with automated continuous agent analysis.",
                strategic_focus="Protect market share against monitoring scrapers by offering verified hallucination-free executive proposals and immediate countermeasure roadmaps."
            )
            db.add(ws)
            db.commit()
            db.refresh(ws)

        print(f"📦 Populating comprehensive test data for workspace: '{ws.name}' ({ws.id})...")

        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)

        # 1. Create a Scan Run record
        scan_run = ScanRun(
            workspace_id=ws.id,
            status="completed",
            total_sources=5,
            successful_sources=5,
            failed_sources=0,
            created_at=yesterday,
            completed_at=yesterday + timedelta(minutes=2)
        )
        db.add(scan_run)
        db.commit()
        db.refresh(scan_run)

        # 2. Setup Competitors & Sources
        competitors_data = [
            {
                "name": "Visualping",
                "domain": "visualping.io",
                "notes": "Leading website change alert service expanding rapidly into enterprise automated CI workflows.",
                "sources": [
                    {
                        "source_type": "pricing",
                        "url": "https://visualping.io/pricing",
                        "change_category": "pricing_change",
                        "is_meaningful": True,
                        "score": 0.98,
                        "summary": "Visualping raised Starter Plan pricing from $10/mo to $14/mo, Business Plan from $50/mo to $75/mo, and added an Enterprise AI Tier starting at $299/mo.",
                        "prev_text": (
                            "Visualping Plans & Pricing\n"
                            "Starter Plan: $10 / mo billed annually ($14 month-to-month). 25 pages monitored every hour.\n"
                            "Business Plan: $50 / mo. 100 pages monitored every 15 minutes. Email alerts included.\n"
                            "Enterprise Plan: Contact sales for custom page limits and dedicated proxies."
                        ),
                        "curr_text": (
                            "Visualping Plans & Pricing\n"
                            "Starter Plan: $14 / mo billed annually ($19 month-to-month). 30 pages monitored every 30 minutes.\n"
                            "Business Plan: $75 / mo. 150 pages monitored every 5 minutes. Includes webhook & Slack alerts.\n"
                            "Enterprise AI Tier: Starting at $299 / mo. Unlimited scans with automated AI summary extraction and team workspaces."
                        ),
                        "diff": (
                            "--- https://visualping.io/pricing (Previous Snapshot)\n"
                            "+++ https://visualping.io/pricing (Current Snapshot)\n"
                            "@@ -2,4 +2,4 @@\n"
                            "-Starter Plan: $10 / mo billed annually ($14 month-to-month). 25 pages monitored every hour.\n"
                            "-Business Plan: $50 / mo. 100 pages monitored every 15 minutes. Email alerts included.\n"
                            "-Enterprise Plan: Contact sales for custom page limits and dedicated proxies.\n"
                            "+Starter Plan: $14 / mo billed annually ($19 month-to-month). 30 pages monitored every 30 minutes.\n"
                            "+Business Plan: $75 / mo. 150 pages monitored every 5 minutes. Includes webhook & Slack alerts.\n"
                            "+Enterprise AI Tier: Starting at $299 / mo. Unlimited scans with automated AI summary extraction and team workspaces."
                        ),
                        "finding_title": "Visualping Commercial Tier Realignment & AI Upsell",
                        "finding_impact": "Visualping increased entry-tier pricing by 40% and launched a dedicated Enterprise AI Tier at $299/mo. This creates a prime commercial opportunity for TradeCraft to target cost-sensitive teams with our freemium tier while highlighting our included AI reasoning.",
                        "finding_action": "Publish a targeted battlecard highlighting TradeCraft's zero-cost open LLM architecture, update comparison landing pages, and launch an outbound campaign to Visualping teams facing renewal hikes."
                    }
                ]
            },
            {
                "name": "Crayon",
                "domain": "crayon.co",
                "notes": "Enterprise competitive intelligence platform specializing in automated market tracking and battlecards.",
                "sources": [
                    {
                        "source_type": "product_page",
                        "url": "https://www.crayon.co/platform",
                        "change_category": "feature_announcement",
                        "is_meaningful": True,
                        "score": 0.92,
                        "summary": "Crayon launched Generative AI Battlecards with real-time CRM deal integration and automated Gong call summary highlights.",
                        "prev_text": (
                            "Crayon Platform Overview\n"
                            "Curate competitive intelligence feeds from over 300 million sources.\n"
                            "Build static sales battlecards with manual editor controls.\n"
                            "Weekly email digests for executive leadership."
                        ),
                        "curr_text": (
                            "Crayon Platform Overview\n"
                            "Curate competitive intelligence feeds from over 300 million sources.\n"
                            "Generative AI Battlecards: Automatically generate real-time deal talk-tracks from competitor website changes with Salesforce and HubSpot bi-directional sync.\n"
                            "Live Gong & Chorus integration for automated customer voice quote attribution."
                        ),
                        "diff": (
                            "--- https://www.crayon.co/platform (Previous Snapshot)\n"
                            "+++ https://www.crayon.co/platform (Current Snapshot)\n"
                            "@@ -3,2 +3,3 @@\n"
                            "-Build static sales battlecards with manual editor controls.\n"
                            "-Weekly email digests for executive leadership.\n"
                            "+Generative AI Battlecards: Automatically generate real-time deal talk-tracks from competitor website changes with Salesforce and HubSpot bi-directional sync.\n"
                            "+Live Gong & Chorus integration for automated customer voice quote attribution."
                        ),
                        "finding_title": "Crayon Real-Time CRM AI Battlecards Launch",
                        "finding_impact": "Crayon is actively eliminating manual battlecard maintenance by using LLMs to sync competitor changes into sales CRM workflows. This threatens our enterprise sales pipeline if our proposal generation is not easily distributable to sales reps.",
                        "finding_action": "Accelerate export and sharing capabilities in TradeCraft, enabling 1-click Markdown and executive proposal export into Slack channels and CRM deal notes."
                    }
                ]
            },
            {
                "name": "Klue",
                "domain": "klue.com",
                "notes": "Market leader in competitive enablement and win-loss intelligence.",
                "sources": [
                    {
                        "source_type": "positioning",
                        "url": "https://klue.com/positioning",
                        "change_category": "positioning_shift",
                        "is_meaningful": True,
                        "score": 0.88,
                        "summary": "Klue shifted homepage hero branding to 'Unified Win-Loss & AI Competitive Enablement', deprecating legacy standalone battlecard packages.",
                        "prev_text": (
                            "Klue: The Competitive Enablement Platform for Enterprise Tech.\n"
                            "Equip your sales team with battlecards that win deals.\n"
                            "Track competitors, collect field intelligence, and measure win rates."
                        ),
                        "curr_text": (
                            "Klue: The Unified Win-Loss & AI Competitive Enablement Platform.\n"
                            "Harness AI-driven win-loss buyer interviews alongside automated competitor tracking.\n"
                            "Deprecation Notice: Standalone Battlecards v1 package is retired in favor of the Complete Intelligence Suite."
                        ),
                        "diff": (
                            "--- https://klue.com/positioning (Previous Snapshot)\n"
                            "+++ https://klue.com/positioning (Current Snapshot)\n"
                            "@@ -1,3 +1,3 @@\n"
                            "-Klue: The Competitive Enablement Platform for Enterprise Tech.\n"
                            "-Equip your sales team with battlecards that win deals.\n"
                            "+Klue: The Unified Win-Loss & AI Competitive Enablement Platform.\n"
                            "+Harness AI-driven win-loss buyer interviews alongside automated competitor tracking.\n"
                            "+Deprecation Notice: Standalone Battlecards v1 package is retired in favor of the Complete Intelligence Suite."
                        ),
                        "finding_title": "Klue Full-Suite Consolidation & Standalone Package Deprecation",
                        "finding_impact": "Klue is forcing all customers onto their higher-priced Complete Intelligence Suite by deprecating standalone battlecard subscriptions. Mid-market accounts are expressing frustration over forced price increases.",
                        "finding_action": "Launch targeted positioning campaign highlighting TradeCraft's modular design where teams can use change tracking and proposal generation without buying an expensive monolithic win-loss contract."
                    }
                ]
            },
            {
                "name": "Semrush",
                "domain": "semrush.com",
                "notes": "SEO, content marketing, and competitive search intelligence suite.",
                "sources": [
                    {
                        "source_type": "blog",
                        "url": "https://www.semrush.com/blog/ai-search-tracking",
                        "change_category": "feature_announcement",
                        "is_meaningful": True,
                        "score": 0.95,
                        "summary": "Semrush announced AI Search Optimization (AISO) tracking to measure competitor brand visibility inside ChatGPT, Claude, and Perplexity answers.",
                        "prev_text": (
                            "Semrush Search Intelligence Blog\n"
                            "Track organic keywords and Google search engine results pages (SERPs).\n"
                            "Monitor competitor paid advertising copy and backlink profiles."
                        ),
                        "curr_text": (
                            "Semrush Search Intelligence Blog\n"
                            "Track organic keywords and Google search engine results pages (SERPs).\n"
                            "AI Search Optimization (AISO): New engine monitoring competitor brand citations and recommendations across ChatGPT, Perplexity, and Google Gemini answers.\n"
                            "Includes sentiment scoring and prompt market share analytics."
                        ),
                        "diff": (
                            "--- https://www.semrush.com/blog/ai-search-tracking (Previous Snapshot)\n"
                            "+++ https://www.semrush.com/blog/ai-search-tracking (Current Snapshot)\n"
                            "@@ -2,2 +2,3 @@\n"
                            "-Monitor competitor paid advertising copy and backlink profiles.\n"
                            "+AI Search Optimization (AISO): New engine monitoring competitor brand citations and recommendations across ChatGPT, Perplexity, and Google Gemini answers.\n"
                            "+Includes sentiment scoring and prompt market share analytics."
                        ),
                        "finding_title": "Semrush AI Search & LLM Engine Monitoring Launch",
                        "finding_impact": "Competitive visibility is shifting beyond traditional Google SEO to generative search engine citations. Semrush's new AISO engine validates that B2B enterprises urgently need visibility into how AI models position them versus rivals.",
                        "finding_action": "Evaluate integrating generative brand citation tracking into TradeCraft's future Phase 6 roadmap to complement web snapshot diffs."
                    }
                ]
            }
        ]

        created_findings = []

        for comp_data in competitors_data:
            # Check or create Competitor
            competitor = db.query(Competitor).filter(
                Competitor.workspace_id == ws.id,
                Competitor.name == comp_data["name"]
            ).first()

            if not competitor:
                competitor = Competitor(
                    workspace_id=ws.id,
                    name=comp_data["name"],
                    website=f"https://{comp_data['domain']}",
                    description=comp_data["notes"],
                    monitoring_enabled=True
                )
                db.add(competitor)
                db.commit()
                db.refresh(competitor)
                print(f"  + Added Competitor: {competitor.name}")

            for src_data in comp_data["sources"]:
                # Check or create Source
                source = db.query(Source).filter(
                    Source.competitor_id == competitor.id,
                    Source.url == src_data["url"]
                ).first()

                if not source:
                    source = Source(
                        competitor_id=competitor.id,
                        name=f"{competitor.name} {src_data['source_type'].title()}",
                        source_type=src_data["source_type"],
                        url=src_data["url"],
                        monitoring_enabled=True
                    )
                    db.add(source)
                    db.commit()
                    db.refresh(source)
                    print(f"    + Added Source: {source.url}")

                # Create Previous Snapshot
                prev_hash = hashlib.sha256(src_data["prev_text"].encode()).hexdigest()
                prev_snap = Snapshot(
                    scan_run_id=scan_run.id,
                    source_id=source.id,
                    status="success",
                    status_code=200,
                    raw_content=src_data["prev_text"],
                    normalized_content=src_data["prev_text"],
                    content_hash=prev_hash,
                    created_at=two_days_ago
                )
                db.add(prev_snap)
                db.commit()
                db.refresh(prev_snap)

                # Create Current Snapshot
                curr_hash = hashlib.sha256(src_data["curr_text"].encode()).hexdigest()
                curr_snap = Snapshot(
                    scan_run_id=scan_run.id,
                    source_id=source.id,
                    status="success",
                    status_code=200,
                    raw_content=src_data["curr_text"],
                    normalized_content=src_data["curr_text"],
                    content_hash=curr_hash,
                    created_at=yesterday
                )
                db.add(curr_snap)
                db.commit()
                db.refresh(curr_snap)

                # Check if Change exists for this source
                existing_change = db.query(Change).filter(
                    Change.workspace_id == ws.id,
                    Change.source_id == source.id,
                    Change.current_snapshot_id == curr_snap.id
                ).first()

                if not existing_change:
                    change_hash = hashlib.sha256(src_data["diff"].encode()).hexdigest()
                    change = Change(
                        workspace_id=ws.id,
                        competitor_id=competitor.id,
                        source_id=source.id,
                        scan_run_id=scan_run.id,
                        previous_snapshot_id=prev_snap.id,
                        current_snapshot_id=curr_snap.id,
                        change_hash=change_hash,
                        change_type="modification",
                        category=src_data["change_category"],
                        is_meaningful=src_data["is_meaningful"],
                        significance_score=src_data["score"],
                        summary=src_data["summary"],
                        diff_unified=src_data["diff"],
                        diff_stats={"lines_added": 3, "lines_removed": 2, "similarity_ratio": 0.65},
                        detected_at=yesterday
                    )
                    db.add(change)
                    db.commit()
                    db.refresh(change)
                    print(f"    + Added Change: {change.category} ({change.summary[:60]}...)")
                else:
                    change = existing_change

                # Create Verified IntelligenceFinding for this change
                existing_finding = db.query(IntelligenceFinding).filter(
                    IntelligenceFinding.change_id == change.id
                ).first()

                if not existing_finding:
                    # Pick a quote from curr_text that exists verbatim
                    sample_quote = None
                    for line in src_data["curr_text"].splitlines():
                        if len(line.strip()) > 20 and "$" in line or "AI" in line or "Platform" in line:
                            sample_quote = line.strip()
                            break
                    if not sample_quote:
                        sample_quote = src_data["curr_text"].splitlines()[-1].strip()

                    char_start = src_data["curr_text"].find(sample_quote)
                    char_end = char_start + len(sample_quote) if char_start != -1 else len(sample_quote)

                    finding = IntelligenceFinding(
                        workspace_id=ws.id,
                        change_id=change.id,
                        title=src_data["finding_title"],
                        category=FindingCategory.PRICING_CHANGE.value if "pricing" in src_data["change_category"] else FindingCategory.FEATURE_RELEASE.value,
                        factual_summary=src_data["summary"],
                        impact_analysis=src_data["finding_impact"],
                        recommended_action=src_data["finding_action"],
                        confidence_level=ConfidenceLevel.HIGH.value,
                        verification_status=VerificationStatus.VERIFIED.value,
                        critic_notes="Critic verified: 100% of candidate claims grounded with exact character offsets in snapshot text.",
                        grounding_score=96.5
                    )
                    db.add(finding)
                    db.commit()
                    db.refresh(finding)

                    # Add Evidence Quote
                    eq = EvidenceQuote(
                        finding_id=finding.id,
                        snapshot_id=curr_snap.id,
                        verbatim_quote=sample_quote,
                        char_offset_start=max(0, char_start),
                        char_offset_end=char_end,
                        source_url=source.url
                    )
                    db.add(eq)
                    db.commit()
                    print(f"      + Added Finding: '{finding.title}' (EGA: {finding.grounding_score}%)")
                    created_findings.append(finding)
                else:
                    created_findings.append(existing_finding)

        # 3. Create High-Quality 7-Section Counter-Proposals
        verified_finding_ids = [f.id for f in created_findings[:2]]

        existing_proposal = db.query(Proposal).filter(
            Proposal.workspace_id == ws.id,
            Proposal.title == "Q4 Strategic Response: Visualping Price Surge & Crayon AI Battlecards"
        ).first()

        if not existing_proposal and verified_finding_ids:
            proposal_content = (
                "# Executive Counter-Proposal: Q4 Competitive Response\n\n"
                "## 1. Problem / Opportunity\n"
                "Recent market telemetry indicates major shifts across core competitive benchmarks. "
                "Visualping has increased entry-tier prices by 40% and launched an expensive $299/mo Enterprise AI tier, "
                "while Crayon has launched automated Generative AI Battlecards connected to sales CRMs. "
                "This creates an immediate commercial opportunity for TradeCraft to capture budget-sensitive B2B teams.\n\n"
                "## 2. Competitor Change\n"
                "1. **Visualping Pricing Shift**: Starter tier raised to $14/mo, Business tier raised to $75/mo, and Enterprise AI tier launched at $299/mo.\n"
                "2. **Crayon Feature Launch**: Generative AI Battlecards with real-time deal alerts synced directly to Salesforce and HubSpot.\n\n"
                "## 3. Evidence\n"
                "> \"Starter Plan: $14 / mo billed annually ($19 month-to-month). 30 pages monitored every 30 minutes.\"\n"
                "*(Source: [https://visualping.io/pricing](https://visualping.io/pricing))*\n\n"
                "> \"Generative AI Battlecards: Automatically generate real-time deal talk-tracks from competitor website changes with Salesforce and HubSpot bi-directional sync.\"\n"
                "*(Source: [https://www.crayon.co/platform](https://www.crayon.co/platform))*\n\n"
                "## 4. Strategic Impact\n"
                "Customer acquisition costs (CAC) for competitive monitoring are increasing across the industry. "
                "Prospects in mid-market tech are actively seeking alternatives to monolithic $15k+/yr enterprise contracts. "
                "Without an immediate countermeasure, our sales team risks losing head-to-head evaluations against Crayon's automated CRM battlecards.\n\n"
                "## 5. Proposed Response\n"
                "Execute a two-pronged commercial and product counter-offensive:\n"
                "- **Commercial**: Position TradeCraft's zero-cost open LLM architecture as the high-accuracy, transparent alternative with guaranteed Evidence Grounding Accuracy ($EGA \\ge 85\\%$).\n"
                "- **Product**: Ship 1-click Markdown and Executive PDF proposal exports to match Crayon's automated sales enablement talk-tracks.\n\n"
                "## 6. Suggested Features/Work\n"
                "- **Phase 1 (Immediate Parity)**: Publish live comparison battlecards highlighting our hallucination-free quote verification.\n"
                "- **Phase 2 (Core Differentiator)**: Implement automated Slack and webhook triggers when meaningful competitor pricing shifts occur.\n"
                "- **Phase 3 (GTM Enablement)**: Launch an outbound campaign targeted at Visualping customers facing renewal price increases.\n\n"
                "## 7. Expected Value\n"
                "- Protect $120,000 in pipeline ARR over the next two quarters.\n"
                "- Increase win rates against Crayon by 18% in mid-market deals.\n"
                "- Elevate customer retention to >95% through transparent, verified evidence citations."
            )

            proposal = Proposal(
                workspace_id=ws.id,
                title="Q4 Strategic Response: Visualping Price Surge & Crayon AI Battlecards",
                target_goal="Capitalize on competitor pricing hikes and neutralize Crayon's automated CRM battlecards",
                markdown_content=proposal_content,
                status=ProposalStatus.DRAFT
            )
            db.add(proposal)
            db.commit()
            print(f"  + Added Sample Proposal: '{proposal.title}'")

        print("\n✅ Successfully seeded comprehensive test data across competitors, sources, snapshots, changes, findings, and proposals!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding test data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_rich_test_data()
