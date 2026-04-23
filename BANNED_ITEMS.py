# ============================================================
# CIRCULARX — No-Trade List (Banned Items Array)
# For AI compliance filter (IRE — Intelligent Routing Engine)
# Sources: Basel Convention Annexes, India HWM Rules 2016
#          (amended 2019), EU Waste Framework Directive /
#          REACH / POP Regulation, Vietnam/Indonesia/Thailand
#          hazardous waste schedules, UAE Federal Law No. 12
#          of 2018 on waste management.
# Usage:  Feed into BERT-based text classifier + CAS number
#         lookup within the Compliance Filter module.
# ============================================================
 
# ----------------------------------------------------------------
# GROUP 1 — GLOBALLY BANNED (Basel Convention Annex / All
#           CircularX jurisdictions: India, Vietnam, Indonesia,
#           Thailand, UAE, EU, USA)
# ----------------------------------------------------------------
GLOBALLY_BANNED = [
 
    # --- Persistent Organic Pollutants (Stockholm Convention) ---
    {
        "item": "Polychlorinated Biphenyls (PCBs)",
        "cas": "1336-36-3",
        "hazard_class": "POP / Toxic",
        "basis": "Basel Convention Annex VIII (A1180); Stockholm Convention Annex A",
        "notes": "Includes PCB-contaminated oils, transformers, capacitors, and electrical equipment containing >50 ppm PCB"
    },
    {
        "item": "Polychlorinated Dibenzo-p-Dioxins (PCDDs) / Furans (PCDFs) — waste streams",
        "cas": "Multiple",
        "hazard_class": "POP / Carcinogenic",
        "basis": "Basel Convention Annex VIII; Stockholm Convention Annex C",
        "notes": "Any waste stream known to contain dioxin/furan contamination above regulatory thresholds"
    },
    {
        "item": "Hexachlorobenzene (HCB) waste",
        "cas": "118-74-1",
        "hazard_class": "POP / Toxic",
        "basis": "Stockholm Convention Annex A; Basel Annex VIII",
        "notes": "Includes HCB-contaminated pesticide wastes and industrial residues"
    },
    {
        "item": "Aldrin, Dieldrin, Endrin waste",
        "cas": "309-00-2 / 60-57-1 / 72-20-8",
        "hazard_class": "POP / Ecotoxic",
        "basis": "Stockholm Convention Annex A",
        "notes": "Obsolete pesticide residues; banned from trade as material inputs"
    },
    {
        "item": "DDT-contaminated waste",
        "cas": "50-29-3",
        "hazard_class": "POP / Ecotoxic",
        "basis": "Stockholm Convention Annex B (restricted); Basel Annex VIII",
        "notes": "Applies to waste streams with DDT concentration above 50 mg/kg"
    },
    {
        "item": "Mirex waste",
        "cas": "2385-85-5",
        "hazard_class": "POP / Toxic",
        "basis": "Stockholm Convention Annex A",
        "notes": "Pesticide residues and contaminated soils"
    },
    {
        "item": "Toxaphene waste",
        "cas": "8001-35-2",
        "hazard_class": "POP / Ecotoxic",
        "basis": "Stockholm Convention Annex A",
        "notes": "Agricultural waste streams containing toxaphene residues"
    },
    {
        "item": "Perfluorooctane Sulfonate (PFOS) and PFOS-related wastes",
        "cas": "1763-23-1",
        "hazard_class": "POP / Persistent",
        "basis": "Stockholm Convention Annex B; EU POP Regulation 2019/1021",
        "notes": "Includes firefighting foam (AFFF) residues, contaminated wastewater sludge, coated textiles"
    },
    {
        "item": "Perfluorooctanoic Acid (PFOA) and PFOA-related wastes",
        "cas": "335-67-1",
        "hazard_class": "POP / Carcinogenic",
        "basis": "Stockholm Convention Annex A; EU POP Regulation",
        "notes": "Includes PTFE manufacturing residues, PFOA-contaminated water treatment sludge"
    },
 
    # --- Asbestos and Asbestos-Containing Wastes ---
    {
        "item": "Asbestos (all forms) — waste and off-cuts",
        "cas": "1332-21-4",
        "hazard_class": "Carcinogenic / Fibrous Hazardous",
        "basis": "Basel Convention Annex VIII (A2060); India HWM Rules Schedule I; EU Directive 87/217/EEC; UAE Federal Law No. 12/2018",
        "notes": "Includes chrysotile, amosite, crocidolite, actinolite, anthophyllite, tremolite in any waste form; construction demolition debris containing asbestos"
    },
 
    # --- Radioactive Wastes ---
    {
        "item": "Radioactive waste — all categories",
        "cas": "N/A",
        "hazard_class": "Radioactive / Ionising Radiation",
        "basis": "IAEA Joint Convention; Basel Convention (excluded — separate regime); national atomic energy legislation in all CircularX jurisdictions",
        "notes": "Low-level, intermediate-level, and high-level radioactive wastes; radioactively contaminated equipment, scrap metal from nuclear facilities"
    },
    {
        "item": "Radioactively contaminated scrap metal",
        "cas": "N/A",
        "hazard_class": "Radioactive",
        "basis": "IAEA Safety Standards; India Atomic Energy Act; EU Council Directive 2013/59/Euratom",
        "notes": "Scrap from decommissioned nuclear plant equipment, radiological measuring devices; requires radiation clearance before any trade"
    },
 
    # --- Mercury and Mercury-Bearing Wastes ---
    {
        "item": "Metallic mercury (waste / off-spec) for non-closed-loop trade",
        "cas": "7439-97-6",
        "hazard_class": "Toxic / Neurotoxic",
        "basis": "Minamata Convention; Basel Convention; EU Mercury Regulation (EU) 2017/852; India HWM Rules",
        "notes": "Elemental mercury from chlor-alkali plant decommissioning, dental amalgam waste; permissible only for certified mercury storage or permitted recycling, NOT general marketplace trade"
    },
    {
        "item": "Mercury-containing equipment waste (thermometers, switches, fluorescent lamps — bulk unprocessed)",
        "cas": "7439-97-6",
        "hazard_class": "Toxic",
        "basis": "Minamata Convention Article 11; Basel Annex VIII",
        "notes": "Bulk unprocessed mixed mercury-lamp or -switch waste; certified WEEE processors only, not open marketplace"
    },
 
    # --- Lead Acid Batteries (unprocessed) ---
    {
        "item": "Unsorted, unprocessed lead-acid battery scrap (cross-border movement)",
        "cas": "N/A",
        "hazard_class": "Toxic / Corrosive",
        "basis": "Basel Convention Annex VIII (A1160); India Battery Waste Management Rules 2022; EU Battery Regulation 2023/1542",
        "notes": "Applies to unprocessed whole-battery scrap traded cross-border; certified smelter-to-smelter movements under OECD Decision C(2001)107 are exempted"
    },
]
 
 
# ----------------------------------------------------------------
# GROUP 2 — INDIA-SPECIFIC BANS
#           (HWM Rules 2016 amended 2019, E-Waste Rules 2022,
#            Plastic Waste Rules 2022, CPCB notifications)
#           Applies to Phase 1 domestic operations (Tamil Nadu,
#           Maharashtra) and any India-origin listings.
# ----------------------------------------------------------------
INDIA_BANNED = [
 
    # --- Schedule I Hazardous Wastes (absolute prohibition on trade as raw material) ---
    {
        "item": "Cyanide process wastes (gold/silver extraction residues)",
        "cas": "57-12-5 (free cyanide)",
        "hazard_class": "Highly Toxic / Lethal",
        "basis": "India HWM Rules 2016 Schedule I Category 35.3; CPCB HW-3",
        "notes": "Heap leach tailings and vat leach residues containing free cyanide; gold mine cyanidation pond effluent sludge"
    },
    {
        "item": "Chromium VI-containing tannery sludge",
        "cas": "18540-29-9",
        "hazard_class": "Carcinogenic / Toxic",
        "basis": "India HWM Rules 2016 Category 18; Supreme Court of India tannery cluster rulings",
        "notes": "Tannery effluent treatment plant (ETP) sludge with Cr(VI) > 0.5 mg/kg; Chrome shavings and trimmings from leather processing"
    },
    {
        "item": "Spent pot liner (SPL) from aluminium smelting",
        "cas": "N/A",
        "hazard_class": "Toxic / Reactive / Cyanide-releasing",
        "basis": "India HWM Rules 2016 Schedule I; Basel Annex VIII (A2050)",
        "notes": "First-cut and second-cut SPL; contains fluorides, cyanides, and PAHs; banned from open trade"
    },
    {
        "item": "Acid tar from petroleum refining / coal tar distillation",
        "cas": "N/A",
        "hazard_class": "Corrosive / Carcinogenic",
        "basis": "India HWM Rules 2016 Category 5 (oil refinery wastes); CPCB notification 2019",
        "notes": "Dark viscous residue from H2SO4 refining of petroleum fractions; contains PAHs, sulfonic acids"
    },
    {
        "item": "Fly ash exceeding Class C heavy metal thresholds (non-CPCB-notified use)",
        "cas": "N/A",
        "hazard_class": "Toxic if above threshold",
        "basis": "India Fly Ash Notification 2021 (MoEFCC); CPCB guidelines",
        "notes": "Fly ash from coal-fired plants is tradeable ONLY for CPCB-approved end uses (cement, bricks, road construction); ash exceeding Hg >0.1 mg/kg or As >100 mg/kg is banned from trade"
    },
    {
        "item": "Chlorinated solvent still bottoms (TCE, PCE residues)",
        "cas": "79-01-6 / 127-18-4",
        "hazard_class": "Carcinogenic / VOC",
        "basis": "India HWM Rules 2016 Category 3; Schedule I hazardous constituents list",
        "notes": "Still bottoms and residues from use of trichloroethylene and tetrachloroethylene in metal degreasing"
    },
    {
        "item": "Single-use plastic waste streams (below 75 microns) — listed under Plastic Waste Rules 2022",
        "cas": "N/A",
        "hazard_class": "Environmental hazard (regulatory ban)",
        "basis": "India Plastic Waste Management (Amendment) Rules 2022; Gazette Notification July 2022",
        "notes": "Includes plastic bags < 75 microns, plastic cutlery, straws, stirrers, polystyrene decoration items; prohibited from marketplace as material input"
    },
    {
        "item": "E-waste mixed with hazardous non-WEEE materials (unsegregated)",
        "cas": "N/A",
        "hazard_class": "Mixed Hazardous",
        "basis": "India E-Waste (Management) Rules 2022; EPR framework",
        "notes": "WEEE mixed with batteries, CRT glass, or mercury-bearing components is prohibited from open trade; must be channelled to CPCB-authorised dismantlers only"
    },
    {
        "item": "Pesticide manufacturing residues (organophosphate / organochlorine)",
        "cas": "Multiple",
        "hazard_class": "Toxic / Neurotoxic",
        "basis": "India HWM Rules 2016 Category 11; Schedule I",
        "notes": "Process residues from pesticide formulation plants; contaminated containers, mother liquors, and filtration sludges"
    },
    {
        "item": "Pharmaceutical manufacturing effluent sludge (API process residues)",
        "cas": "Multiple",
        "hazard_class": "Toxic / Antimicrobial Resistance risk",
        "basis": "India HWM Rules 2016 Category 18; CPCB pharmaceutical cluster notifications (Hyderabad, Vapi, Ankleshwar)",
        "notes": "ETP sludge from bulk drug manufacturing containing active pharmaceutical ingredient (API) residues; not tradeable as raw material input"
    },
]
 
 
# ----------------------------------------------------------------
# GROUP 3 — SOUTHEAST ASIA BANS: Vietnam, Indonesia, Thailand
#           (Phase 2 expansion jurisdictions)
#           Vietnam: Decree 08/2022/ND-CP; Indonesia: PP 22/2021,
#           PermenLHK P.12/2020; Thailand: Hazardous Substance
#           Act B.E. 2535 (amended 2019)
# ----------------------------------------------------------------
SOUTHEAST_ASIA_BANNED = [
 
    # --- Shared across Vietnam, Indonesia, Thailand ---
    {
        "item": "Ship-breaking waste streams — asbestos insulation, bilge sludge, PCB-containing paint",
        "cas": "Multiple",
        "hazard_class": "Mixed Hazardous",
        "basis": "Hong Kong International Convention (ratified: all three jurisdictions); Basel Convention",
        "notes": "Ship recycling waste containing asbestos lagging, PCB-based anti-fouling paint scrapings, heavy fuel oil sludge; applies to vessels being broken in Vietnam/Indonesia/Thailand yards"
    },
    {
        "item": "Waste containing Brominated Flame Retardants (PBDEs) — WEEE plastics",
        "cas": "32534-81-9 (PBDE mix)",
        "hazard_class": "POP / Endocrine disruptor",
        "basis": "Stockholm Convention (penta-BDE, octa-BDE Annex A); Vietnam Circular 36/2015; Indonesia PermenLHK P.12/2020",
        "notes": "Printed circuit boards, plastic casings from pre-2006 electronics containing PBDE flame retardants"
    },
    {
        "item": "Imported plastic waste failing Basel plastic waste amendment criteria (mixed / contaminated)",
        "cas": "N/A",
        "hazard_class": "Environmental hazard",
        "basis": "Basel Convention plastic waste amendment (effective Jan 2021); Vietnam Decree 08/2022; Indonesia MoEF Regulation",
        "notes": "Hazardous or contaminated plastic waste imports; unrecyclable mixed plastic bales; Vietnam and Indonesia have banned import of low-quality plastic scrap"
    },
 
    # --- Vietnam-specific ---
    {
        "item": "Used motor oil / lubricant waste (below regeneration-grade, for unrestricted resale)",
        "cas": "N/A",
        "hazard_class": "Toxic / Carcinogenic (PAHs)",
        "basis": "Vietnam Decree 08/2022/ND-CP Annex II; MONRE Circular 02/2022",
        "notes": "Spent engine oil failing Vietnamese QCVN quality standard for regenerated base oil; not tradeable as raw material; must go to licensed co-processing or regeneration facilities only"
    },
 
    # --- Indonesia-specific ---
    {
        "item": "Palm oil mill effluent (POME) sludge — untreated, above BOD threshold",
        "cas": "N/A",
        "hazard_class": "High BOD / Methane-generating",
        "basis": "Indonesia PP 22/2021 (Hazardous Waste List B3); Ministry of Environment Regulation",
        "notes": "Untreated POME sludge with BOD > 5000 mg/L; banned from open material trade; must go to biogas or composting certified facility"
    },
    {
        "item": "Nickel laterite processing acid waste (mixed sulfate/acid leach residues)",
        "cas": "N/A",
        "hazard_class": "Toxic / Corrosive",
        "basis": "Indonesia PP 22/2021; ESDM regulation on nickel processing",
        "notes": "Residues from HPAL (High Pressure Acid Leach) processing of nickel laterite ore; contains Mn, Cr, Ni at toxic concentrations"
    },
 
    # --- Thailand-specific ---
    {
        "item": "Electroplating sludge containing cyanide or hexavalent chromium",
        "cas": "Multiple",
        "hazard_class": "Toxic / Carcinogenic",
        "basis": "Thailand Hazardous Substance Act B.E. 2535; Notification of Ministry of Industry on Hazardous Industrial Wastes",
        "notes": "Filter cake from electroplating rinse water treatment; Cr(VI) > 5 mg/kg or CN > 250 mg/kg triggers ban"
    },
    {
        "item": "Waste foundry sand (furan resin bonded) — above phenol/formaldehyde threshold",
        "cas": "N/A",
        "hazard_class": "Toxic leachate risk",
        "basis": "Thailand Pollution Control Department; Basel Convention Annex IX B2080 (note: if exceeds leachate thresholds, transitions to Annex VIII)",
        "notes": "Furan-resin bonded spent foundry sand with TCLP phenol leachate > 14.4 mg/L is banned; green sand below threshold is tradeable"
    },
]
 
 
# ----------------------------------------------------------------
# GROUP 4 — UAE-SPECIFIC BANS
#           UAE Federal Law No. 12 of 2018 on Integrated Waste
#           Management; Ministerial Decision 378/2018;
#           Abu Dhabi EAD and Dubai Municipality regulations.
# ----------------------------------------------------------------
UAE_BANNED = [
 
    {
        "item": "Healthcare / clinical waste (sharps, pathological, infectious) — unsterilised",
        "cas": "N/A",
        "hazard_class": "Biohazardous / Infectious",
        "basis": "UAE Federal Law 12/2018 Article 11; Dubai Municipality Healthcare Waste Regulation HE-REG-002",
        "notes": "Untreated clinical waste including sharps, surgical residues, cultures, pathological materials; must be autoclave-sterilised before any movement; banned from open marketplace entirely"
    },
    {
        "item": "Construction and demolition debris containing gypsum wallboard mixed with organic waste",
        "cas": "N/A",
        "hazard_class": "H2S-generating (Landfill Gas hazard)",
        "basis": "UAE Ministerial Decision 378/2018; Abu Dhabi EAD CW regulations",
        "notes": "Gypsum C&D waste co-mingled with biodegradable materials generates toxic H2S; banned from open material trade; segregated gypsum board without organic contamination is tradeable"
    },
    {
        "item": "Sludge from desalination plant brine concentrate (above heavy metal discharge limits)",
        "cas": "N/A",
        "hazard_class": "Ecotoxic (marine)",
        "basis": "UAE Federal Law 24/1999 (Environment); Abu Dhabi EAD coastal discharge regulations",
        "notes": "Brine sludge from MSF/RO desalination with heavy metal concentration above ADSSC/EAD discharge thresholds; not tradeable as material input"
    },
    {
        "item": "Hydrocarbon-contaminated sand / drill cuttings from oil and gas operations",
        "cas": "N/A",
        "hazard_class": "Toxic (TPH contamination)",
        "basis": "UAE Ministerial Decision 37/2006 (Oil and Gas waste); ADNOC Waste Management Standards",
        "notes": "Oil-based mud drill cuttings with Total Petroleum Hydrocarbons (TPH) > 1% are banned from open material trade; must go to ADNOC-approved thermal desorption or bioremediation facility"
    },
    {
        "item": "Fly ash from oil-fired power plants exceeding UAE heavy metals limits",
        "cas": "N/A",
        "hazard_class": "Toxic",
        "basis": "UAE Cabinet Decision 37/2001; EAD waste characterisation thresholds",
        "notes": "Residual fuel oil (RFO) fly ash with V > 1000 mg/kg or Ni > 300 mg/kg banned from unregulated material trade; high-vanadium fly ash is a controlled regulated hazardous waste in UAE"
    },
]
 
 
# ----------------------------------------------------------------
# GROUP 5 — EU / NORTH AMERICA BANS
#           (Phase 3 expansion — EU WFD 2008/98/EC, REACH
#            Regulation EC 1907/2006, EU POP Regulation
#            2019/1021; US EPA RCRA Hazardous Waste rules,
#            TSCA Section 6)
# ----------------------------------------------------------------
EU_NORTH_AMERICA_BANNED = [
 
    # --- EU ---
    {
        "item": "SVHC-listed substance waste streams (REACH Candidate List substances above 0.1% w/w)",
        "cas": "Multiple (ECHA Candidate List)",
        "hazard_class": "CMR / Endocrine disruptor / PBT",
        "basis": "EU REACH Regulation EC 1907/2006 Article 59; EU Waste Framework Directive",
        "notes": "Includes waste containing: bisphenol A (BPA) >0.1%, lead compounds, phthalates (DEHP/BBP/DBP/DIBP), short-chain chlorinated paraffins (SCCP), cadmium compounds; traded as waste only to authorised SVHC treatment facilities"
    },
    {
        "item": "WEEE containing cathode ray tubes (CRTs) — unprocessed",
        "cas": "N/A",
        "hazard_class": "Toxic (lead glass)",
        "basis": "EU WEEE Directive 2012/19/EU Annex VII; Basel Annex VIII (A1180)",
        "notes": "Whole or crushed CRT glass containing >2% lead by weight; unprocessed CRT scrap is banned from open marketplace; certified glass-to-glass recyclers only"
    },
    {
        "item": "Halogenated solvent wastes (dichloromethane, chloroform, carbon tetrachloride)",
        "cas": "75-09-2 / 67-66-3 / 56-23-5",
        "hazard_class": "Toxic / ODS / Carcinogenic",
        "basis": "EU Waste Framework Directive Annex III (HP14 ecotoxic); Montreal Protocol (CTC); REACH SVHC",
        "notes": "Spent halogenated solvent mixtures from cleaning, degreasing, or pharmaceutical operations; carbon tetrachloride is an ODS; all three are SVHC candidates"
    },
    {
        "item": "Waste containing polycyclic aromatic hydrocarbons (PAH) above EU threshold (coal tar pitch)",
        "cas": "65996-93-2 (CTP)",
        "hazard_class": "Carcinogenic / PBT",
        "basis": "EU REACH SVHC (benzo[a]pyrene CAS 50-32-8); EU CLP Regulation; Basel Annex VIII (A3200)",
        "notes": "Coal tar pitch waste and PAH-containing road extraction materials with B[a]P > 50 mg/kg banned from open material trade"
    },
    {
        "item": "Ozone-depleting substance (ODS) waste — HCFCs, CFCs, Halons",
        "cas": "Multiple",
        "hazard_class": "ODS / GHG",
        "basis": "Montreal Protocol; EU ODS Regulation 1005/2009; US EPA Section 608 SNAP",
        "notes": "Waste refrigerant gases, foam blowing agent residues, fire-suppression halon cylinders; must go to certified ODS destruction or recovery facilities; not open material trade"
    },
 
    # --- US / North America ---
    {
        "item": "RCRA-listed hazardous wastes — F-list spent solvents (F001–F005)",
        "cas": "Multiple",
        "hazard_class": "Toxic / Ignitable",
        "basis": "US EPA RCRA 40 CFR Part 261 Subpart D",
        "notes": "Spent halogenated and non-halogenated solvents from degreasing: F001 (TCE, PCE, methylene chloride), F002, F003 (acetone, MIBK, MEK), F004, F005 (toluene, benzene); banned from open material trade; Land Disposal Restriction (LDR) treatment required"
    },
    {
        "item": "RCRA K-list wastes — specific industry hazardous waste streams",
        "cas": "Multiple",
        "hazard_class": "Toxic",
        "basis": "US EPA RCRA 40 CFR Part 261 Subpart D (K-list)",
        "notes": "Includes K001 (creosote-treated wood preserving wastewater treatment sludge), K048–K052 (petroleum refinery API separator sludge), K062 (spent pickle liquor from steel finishing); cannot be traded on open marketplace"
    },
    {
        "item": "Polychlorinated Naphthalenes (PCNs) waste",
        "cas": "70776-03-3",
        "hazard_class": "POP / Toxic",
        "basis": "US TSCA Section 6; Stockholm Convention listing (2015); EPA Rule 2019",
        "notes": "Wire insulation, capacitor impregnants from pre-1980 electrical equipment; PCN-contaminated wastes subject to same restrictions as PCBs"
    },
    {
        "item": "PFAS-contaminated industrial sludge / soil (above EPA action level)",
        "cas": "Multiple (PFAS family)",
        "hazard_class": "POP / Carcinogenic",
        "basis": "US EPA PFAS Strategic Roadmap 2021; EPA Hazardous Substance designation (2024) for PFOA, PFOS under CERCLA; Canada CEPA PFAS restrictions",
        "notes": "Sludge from wastewater treatment of PFAS-contaminated industrial effluent; AFFF-contaminated soil; EPA PFAS soil screening level 0.1 µg/kg triggers prohibition on open trade"
    },
]
 
 
# ----------------------------------------------------------------
# GROUP 6 — CROSS-CUTTING BANS (apply across ALL jurisdictions
#           regardless of phase; platform-level policy, not
#           jurisdiction-specific)
# ----------------------------------------------------------------
PLATFORM_UNIVERSAL_BANNED = [
 
    {
        "item": "Uncharacterised mixed hazardous waste (no material data or CAS identification)",
        "cas": "Unknown",
        "hazard_class": "Unknown / Default Hazardous",
        "basis": "CircularX Platform Participation Agreement; Basel Convention precautionary principle",
        "notes": "Any material submitted with insufficient characterisation data to determine hazard class is auto-blocked pending manual review; seller receives structured compliance alert"
    },
    {
        "item": "Biological / biomedical research waste (GMO-containing, infectious agents)",
        "cas": "N/A",
        "hazard_class": "Biohazardous / Biosafety Level 2+",
        "basis": "Cartagena Protocol on Biosafety; national biosafety regulations (all jurisdictions)",
        "notes": "Includes cell culture residues, fermentation waste from recombinant organism processes, viral vector production residues; requires biosafety authority clearance before any movement"
    },
    {
        "item": "Conflict minerals waste — coltan, cassiterite, wolframite, gold from conflict zones",
        "cas": "N/A",
        "hazard_class": "Regulatory / Due Diligence",
        "basis": "EU Conflict Minerals Regulation 2017/821; US Dodd-Frank Act Section 1502; OECD Due Diligence Guidance",
        "notes": "Smelter residues or processing waste from minerals traceable to conflict-affected or high-risk areas without RMAP/ITSCI chain-of-custody documentation; banned from platform"
    },
    {
        "item": "Counterfeit or mislabelled hazardous chemical waste",
        "cas": "N/A",
        "hazard_class": "Fraudulent / Variable Hazard",
        "basis": "CircularX Platform Participation Agreement Section 12.4; national criminal fraud statutes",
        "notes": "Any material submitted under false material identity, tampered CAS number, or misrepresented hazard classification triggers permanent seller deregistration and regulatory referral"
    },
    {
        "item": "Unexploded ordnance or military explosive residues",
        "cas": "N/A",
        "hazard_class": "Explosive / Lethal",
        "basis": "International humanitarian law; national explosive regulations (all jurisdictions)",
        "notes": "Applies to metal scrap from demolition sites, military salvage, or ranges that may contain explosive residues; requires EOD clearance certificate before scrap trade"
    },
    {
        "item": "Narcotics precursor chemical waste (Schedule I / II precursors)",
        "cas": "Multiple (UN Tables I & II)",
        "hazard_class": "Controlled Substance / Regulatory",
        "basis": "UN Convention Against Illicit Traffic in Narcotic Drugs 1988; INCB Precursor Control; India NDPS Act; UAE AML/CFT regulations",
        "notes": "Process waste from legitimate pharmaceutical or chemical manufacture containing traceable concentrations of acetic anhydride, ephedrine, pseudoephedrine, phenylacetic acid, etc.; must be routed through licensed destruction only"
    },
]
 
 
# ----------------------------------------------------------------
# MASTER LIST — combined array for AI classifier ingestion
# ----------------------------------------------------------------
CIRCULARX_NO_TRADE_LIST = (
    GLOBALLY_BANNED
    + INDIA_BANNED
    + SOUTHEAST_ASIA_BANNED
    + UAE_BANNED
    + EU_NORTH_AMERICA_BANNED
    + PLATFORM_UNIVERSAL_BANNED
)
 
 