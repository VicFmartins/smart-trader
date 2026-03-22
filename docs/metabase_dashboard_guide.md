# Metabase Executive Dashboard Guide

This guide turns the CarteiraConsol analytics layer into a polished, fintech-style Metabase experience suitable for portfolio presentation, demos, and executive review.

It assumes these PostgreSQL analytics views already exist:

- `analytics_position_facts`
- `analytics_allocation_by_asset_class`
- `analytics_positions_by_broker`
- `analytics_positions_by_client`
- `analytics_portfolio_totals_by_reference_date`

Use this guide together with [metabase_dashboard_queries.sql](C:/Users/vitor/OneDrive/Documentos/Playground/carteiraconsol/sql/metabase_dashboard_queries.sql).

## Design Goal

The dashboard should feel:

- premium
- clean
- executive
- modern
- fintech-oriented

The narrative flow should always be:

1. KPIs
2. Allocation
3. Exposure
4. Timeline
5. Details

Do not overload the main dashboard. Treat it like a portfolio cover page, not a data dump.

## Dashboard Identity

Recommended dashboard name:

- `CarteiraConsol | Executive Portfolio Overview`

Recommended collection:

- `CarteiraConsol / Executive Dashboard`

Recommended main dashboard card count:

- `9` cards

Recommended secondary saved questions:

- `3` companion questions for exploration, not pinned by default

## Visual Style System

### Theme Strategy

Prefer one of these two visual directions:

- Light executive:
  - white or very light gray dashboard background
  - clean white cards
  - dark text
  - restrained accent colors
- Dark fintech:
  - charcoal or near-black dashboard background
  - slightly lighter cards
  - bright text
  - restrained cyan/teal/blue accents

If you want the safest premium look in Metabase, use the light executive route and let the charts carry the color.

### Recommended Palette

Use a restrained palette. Avoid rainbow dashboards.

- Primary ink: `#0F172A`
- Secondary ink: `#334155`
- Neutral line: `#CBD5E1`
- Accent blue: `#2563EB`
- Accent teal: `#0F766E`
- Accent cyan: `#0891B2`
- Highlight gold: `#B98900`

Usage guidance:

- KPIs: neutral card background, one accent tone per metric if needed
- Allocation: blue/teal family
- Broker exposure: blue family
- Client exposure: teal/cyan family
- Timeline: one strong accent line only
- Tables: neutral, minimal emphasis

### Layout Principles

- keep the KPI row symmetrical
- leave generous spacing between sections
- avoid more than one dense table on the main page
- use only a few chart types repeatedly
- sort all ranking visuals descending by value
- keep labels short and executive

## Build This In 15 Minutes

1. Prepare data and views:

```powershell
cd C:\Users\vitor\OneDrive\Documentos\Playground\carteiraconsol
python scripts/init_db.py
python scripts/run_etl.py --sample
python scripts/create_analytics_views.py
```

2. Start Metabase:

```powershell
docker run -d --name metabase-carteiraconsol -p 3001:3000 metabase/metabase:latest
```

3. Open:

```text
http://localhost:3001
```

4. Connect PostgreSQL:

- Database type: `PostgreSQL`
- Display name: `CarteiraConsol Local`
- Host: `host.docker.internal`
- Port: `5432`
- Database name: `etl_db`
- Username: `postgres`
- Password: `postgres`

5. Create the collection:

- `CarteiraConsol / Executive Dashboard`

6. Use the SQL editor and copy the card queries from [metabase_dashboard_queries.sql](C:/Users/vitor/OneDrive/Documentos/Playground/carteiraconsol/sql/metabase_dashboard_queries.sql).

7. Save each question with the names below.

8. Create the main dashboard and add the primary questions in the recommended order.

9. Add filters and map them only where useful.

## Primary vs Secondary Cards

Primary cards go on the main executive dashboard:

1. `Portfolio AUM`
2. `Client Base`
3. `Broker Network`
4. `Tracked Positions`
5. `Capital Allocation`
6. `Broker Exposure`
7. `Client Exposure`
8. `Portfolio Trajectory`
9. `Position Ledger`

Secondary cards should be saved for drill-down or a second dashboard:

- `Allocation Mix`
- `Broker Footprint`
- `Client Concentration`

## Filter UX Strategy

### Clean Filter Set

Show these by default at the dashboard top:

- `reference_date`
- `broker`
- `asset_class`
- `client_name`

This is the cleanest executive setup.

### Advanced Filter Set

Keep this as optional or collapsed if possible:

- `risk_profile`

Use advanced filters only when the dashboard is being explored, not when it is being presented.

### Filter Mapping

Use Field Filters in Metabase SQL questions:

- `reference_date` -> `analytics_position_facts.reference_date`
- `client_name` -> `analytics_position_facts.client_name`
- `broker` -> `analytics_position_facts.broker`
- `asset_class` -> `analytics_position_facts.asset_class`
- `risk_profile` -> `analytics_position_facts.risk_profile`

## Card-by-Card Build Spec

Each card below includes:

- saved question name
- source
- purpose
- recommended chart type
- recommended title
- recommended description
- visualization settings

### Section 1: Executive Header

#### 1. Portfolio AUM

- Saved question name: `Portfolio AUM`
- Source: `analytics_position_facts`
- Purpose: current total portfolio value after dashboard filters
- Chart type: `KPI`
- Card title: `Portfolio AUM`
- Description: `Current total portfolio value across the filtered investment universe.`
- Visualization settings:
  - number format: currency
  - currency: BRL
  - decimals: 2
  - comparison: off unless you later add prior-period logic
  - iconography: none
  - color: primary blue accent only if Metabase theme supports it

#### 2. Client Base

- Saved question name: `Client Base`
- Source: `analytics_position_facts`
- Purpose: distinct clients represented
- Chart type: `KPI`
- Card title: `Client Base`
- Description: `Number of clients represented in the current portfolio scope.`
- Visualization settings:
  - number format: integer
  - decimals: 0
  - color: neutral or teal

#### 3. Broker Network

- Saved question name: `Broker Network`
- Source: `analytics_position_facts`
- Purpose: distinct brokers represented
- Chart type: `KPI`
- Card title: `Broker Network`
- Description: `Number of broker relationships reflected in the selected portfolio slice.`
- Visualization settings:
  - number format: integer
  - decimals: 0
  - color: neutral or cyan

#### 4. Tracked Positions

- Saved question name: `Tracked Positions`
- Source: `analytics_position_facts`
- Purpose: count of position rows
- Chart type: `KPI`
- Card title: `Tracked Positions`
- Description: `Total number of portfolio positions currently included in the analysis.`
- Visualization settings:
  - number format: integer
  - decimals: 0
  - color: neutral

### Section 2: Allocation Overview

#### 5. Capital Allocation

- Saved question name: `Capital Allocation`
- Source: `analytics_position_facts`
- Purpose: capital split by asset class
- Chart type: `Donut`
- Card title: `Capital Allocation`
- Description: `Portfolio composition by asset class, highlighting where capital is concentrated.`
- Visualization settings:
  - metric: `total_value`
  - breakout: `asset_class`
  - sort: descending by `total_value`
  - number format: currency
  - decimals: 2
  - legend: right side if space allows, otherwise bottom
  - labels: category plus percentage if readable
  - colors:
    - fixed_income: deep blue
    - equities: teal
    - crypto: cyan
    - funds: slate blue
    - others: light gray

### Section 3: Exposure

#### 6. Broker Exposure

- Saved question name: `Broker Exposure`
- Source: `analytics_position_facts`
- Purpose: concentration by broker
- Chart type: `Horizontal Bar`
- Card title: `Broker Exposure`
- Description: `Capital distribution across brokers, showing platform concentration and diversification.`
- Visualization settings:
  - X-axis: `total_value`
  - Y-axis: `broker`
  - sort: descending by `total_value`
  - number format: currency
  - decimals: 2
  - legend: off
  - labels: on if readable
  - bar color: blue

#### 7. Client Exposure

- Saved question name: `Client Exposure`
- Source: `analytics_position_facts`
- Purpose: concentration by client
- Chart type: `Horizontal Bar`
- Card title: `Client Exposure`
- Description: `Top clients ranked by portfolio value within the selected scope.`
- Visualization settings:
  - X-axis: `total_value`
  - Y-axis: `client_name`
  - sort: descending by `total_value`
  - limit: top 10
  - number format: currency
  - decimals: 2
  - legend: off
  - labels: on if readable
  - bar color: teal

### Section 4: Timeline

#### 8. Portfolio Trajectory

- Saved question name: `Portfolio Trajectory`
- Source: `analytics_position_facts`
- Purpose: total portfolio value over time
- Chart type: `Line`
- Card title: `Portfolio Trajectory`
- Description: `Portfolio total value by reference date, showing the evolution of the consolidated book.`
- Visualization settings:
  - X-axis: `reference_date`
  - Y-axis: `portfolio_total_value`
  - sort: ascending by `reference_date`
  - number format: currency
  - decimals: 2
  - markers: off for dense history, on for short history
  - line width: medium
  - fill area: off for a cleaner executive look
  - color: one strong blue or cyan line only

### Section 5: Details

#### 9. Position Ledger

- Saved question name: `Position Ledger`
- Source: `analytics_position_facts`
- Purpose: detailed drill-down
- Chart type: `Table`
- Card title: `Position Ledger`
- Description: `Detailed position-level view for validation, drill-down, and portfolio review.`
- Visualization settings:
  - sort: `reference_date DESC`, then `total_value DESC`
  - visible columns:
    - `reference_date`
    - `client_name`
    - `risk_profile`
    - `broker`
    - `asset_class`
    - `ticker`
    - `normalized_name`
    - `quantity`
    - `avg_price`
    - `total_value`
  - currency columns: `avg_price`, `total_value`
  - decimals:
    - `quantity`: 2 to 8 depending on product mix
    - `avg_price`: 2
    - `total_value`: 2
  - row density: compact or normal
  - pagination: on

## Secondary Exploration Cards

These should be saved in the same collection but not pinned to the main dashboard by default.

### Allocation Mix

- Best use: companion ranking to the donut
- Chart type: `Horizontal Bar`
- Title: `Allocation Mix`
- Description: `Ranked comparison of asset class exposure and portfolio breadth.`

### Broker Footprint

- Best use: operational complement to broker exposure
- Chart type: `Table`
- Title: `Broker Footprint`
- Description: `Broker summary with total value, positions, and client breadth.`

### Client Concentration

- Best use: compact concentration view for advisory or sales demos
- Chart type: `Table`
- Title: `Client Concentration`
- Description: `Client-level concentration, breadth, and risk profile summary.`

## Recommended Layout Grid

Use this structure when arranging the dashboard in Metabase.

### Row 1: KPI Header

- `Portfolio AUM`
- `Client Base`
- `Broker Network`
- `Tracked Positions`

Layout guidance:

- make all four cards the same width
- keep them in one line on desktop
- use short card heights

### Row 2: Allocation and Broker Exposure

- left: `Capital Allocation`
- right: `Broker Exposure`

Layout guidance:

- make these the two visual anchors after the KPI row
- keep similar height for symmetry

### Row 3: Client Exposure and Portfolio Trajectory

- left: `Client Exposure`
- right: `Portfolio Trajectory`

Layout guidance:

- give the line chart slightly more width if your data history grows
- keep the bar chart tall enough for label readability

### Row 4: Detailed Positions

- full width: `Position Ledger`

Layout guidance:

- reserve the full width for the table
- do not place another table beside it

## How To Save and Pin Cards In Metabase

For each SQL query:

1. Open the SQL editor in Metabase.
2. Paste the query from [metabase_dashboard_queries.sql](C:/Users/vitor/OneDrive/Documentos/Playground/carteiraconsol/sql/metabase_dashboard_queries.sql).
3. Configure variables as Field Filters where applicable.
4. Run the query.
5. Choose the recommended chart type.
6. Apply the visualization settings from this guide.
7. Save the question using the exact saved question name.
8. Save it into `CarteiraConsol / Executive Dashboard`.

After the questions are saved:

1. Create a dashboard named `CarteiraConsol | Executive Portfolio Overview`.
2. Add the 9 primary questions.
3. Arrange them in the recommended section order.
4. Add dashboard filters.
5. Map each filter only to compatible cards.

## Narrative Flow For Stakeholders

Use the dashboard like a story:

- start with `Portfolio AUM` and the KPI header to frame scale
- move to `Capital Allocation` to explain composition
- use `Broker Exposure` and `Client Exposure` to explain concentration
- show `Portfolio Trajectory` to frame evolution
- use `Position Ledger` only as the final drill-down layer

This keeps the stakeholder discussion strategic before it becomes operational.

## Clutter Reduction Rules

- keep only one donut on the page
- keep only one line chart on the page
- keep only one detailed table on the page
- avoid adding both optional companion tables to the main dashboard
- hide unnecessary legends
- do not repeat the same metric in multiple visuals unless the storytelling is different

## Presentation Mode Checklist

Before showing the dashboard to stakeholders:

- confirm the latest ETL run completed successfully
- verify the dashboard is filtered to the intended `reference_date`
- check that currency formatting is applied consistently
- confirm all ranking charts are sorted descending
- hide unused filters if your Metabase setup allows it
- collapse or avoid secondary questions on the main page
- ensure card titles are short and polished
- remove noisy legends or redundant labels
- maximize browser zoom for readability if presenting on a large screen
- test the dashboard once in a clean browser tab before the meeting

## Future Upgrades

Useful future improvements when more history is available:

- multi-date trend analysis by broker
- multi-date trend analysis by asset class
- top-N concentration analysis with cumulative share of AUM
- threshold or alert-style cards for excessive broker concentration
- snapshot comparison cards for current versus previous reference date

For now, keep the dashboard disciplined and presentation-ready rather than feature-heavy.
