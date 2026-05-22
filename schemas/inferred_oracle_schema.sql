-- ────────────────────────────────────────────────────────────────
-- inferred_oracle_schema.sql
-- INFERRED Oracle DDL — Phase 5 deliverable.
--
-- Source of inference:
--   • DTO property catalogue from MProgService metadata (Phase 2).
--   • SQL templates recovered from the #US heap (Phase 4) which name
--     the actual Oracle table identifiers and confirm a subset of
--     columns. The full column lists are extrapolated from the DTOs
--     that map to each table.
--
-- This file IS NOT a faithful schema dump. The DBA must reconcile it
-- against the live database before any production use. Specifically:
--   • All VARCHAR2 lengths are conservative defaults — adjust to match
--     the on-disk column definitions.
--   • NUMBER precision/scale is inferred from the .NET type, not from
--     observation of stored values.
--   • Foreign keys are inferred from SQL JOIN patterns in #US —
--     they are likely correct but not exhaustively verified.
--   • Indexes implied by WHERE clauses are listed in the trailing
--     `-- Suggested indexes` section.
--
-- Confidence: 70-80% per object (see analysis/05_ORACLE_INTEGRATION.md).
-- ────────────────────────────────────────────────────────────────

-- ────────────────────────────────────────────────────────────────
-- USER_R  (inferred from DTO: Users)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE USER_R (
  NOU                    NUMBER(10,0)    NOT NULL  -- from Users,
  NAME_U                 VARCHAR2(255)             -- from Users,
  NOA                    NUMBER(10,0)              -- from Users,
  ED                     NUMBER(10,0)              -- from Users,
  DE                     NUMBER(10,0)              -- from Users,
  S_K                    NUMBER(10,0)              -- from Users,
  S_S                    NUMBER(10,0)              -- from Users,
  REP                    NUMBER(10,0)              -- from Users,
  SYS                    NUMBER(10,0)              -- from Users,
  PASS                   VARCHAR2(255)             -- from Users,
  access_token           VARCHAR2(255)             -- from Users,
  version                VARCHAR2(255)             -- from Users,
  error_no               NUMBER(10,0)              -- from Users,
  error_msg              VARCHAR2(255)             -- from Users,
  date_server            VARCHAR2(255)             -- from Users
  , CONSTRAINT pk_user_r PRIMARY KEY (NOU)
);

-- ────────────────────────────────────────────────────────────────
-- USER_MNATK  (inferred from DTO: UserPlaces)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE USER_MNATK (
  NOU                    NUMBER(10,0)    NOT NULL  -- from (synthesised PK — not projected by any DTO; inferred from SQL JOIN patterns),
  no_mstlm               VARCHAR2(255)   NOT NULL  -- from UserPlaces,
  num                    VARCHAR2(255)             -- from UserPlaces,
  name                   VARCHAR2(255)             -- from UserPlaces,
  RED                    VARCHAR2(255)             -- from UserPlaces,
  SDAD                   VARCHAR2(255)             -- from UserPlaces
  , CONSTRAINT pk_user_mnatk PRIMARY KEY (NOU, no_mstlm)
);

-- ────────────────────────────────────────────────────────────────
-- data_acc  (inferred from DTO: Accounts)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE data_acc (
  NOA                    NUMBER(10,0)    NOT NULL  -- from (synthesised PK — not projected by any DTO; inferred from SQL JOIN patterns),
  type                   NUMBER(10,0)              -- from Accounts,
  name                   VARCHAR2(255)             -- from Accounts,
  num                    VARCHAR2(255)             -- from Accounts,
  mden                   NUMBER                    -- from Accounts,
  dain                   NUMBER                    -- from Accounts,
  balance                NUMBER                    -- from Accounts,
  notblh                 VARCHAR2(255)             -- from Accounts,
  nomstlm                VARCHAR2(255)             -- from Accounts,
  noadad                 VARCHAR2(255)             -- from Accounts,
  nog                    VARCHAR2(255)             -- from Accounts,
  tel                    VARCHAR2(255)             -- from Accounts,
  statH                  NUMBER(10,0)              -- from Accounts,
  namet                  VARCHAR2(255)             -- from Accounts,
  namep                  VARCHAR2(255)             -- from Accounts
  , CONSTRAINT pk_data_acc PRIMARY KEY (NOA)
);

-- ────────────────────────────────────────────────────────────────
-- GRP  (inferred from DTOs: pGroup, Grops)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE GRP (
  NOG                    NUMBER(10,0)    NOT NULL  -- from (synthesised PK — not projected by any DTO; inferred from SQL JOIN patterns),
  num                    VARCHAR2(255)             -- from pGroup,
  name                   VARCHAR2(255)             -- from pGroup, Grops,
  nomk2                  VARCHAR2(255)             -- from pGroup,
  no                     VARCHAR2(255)             -- from Grops
  , CONSTRAINT pk_grp PRIMARY KEY (NOG)
);

-- ────────────────────────────────────────────────────────────────
-- amlh  (inferred from DTO: Currency)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE amlh (
  no                     NUMBER(10,0)    NOT NULL  -- from (synthesised PK — not projected by any DTO; inferred from SQL JOIN patterns),
  name                   VARCHAR2(255)             -- from Currency,
  num                    VARCHAR2(255)             -- from Currency,
  fls                    VARCHAR2(255)             -- from Currency,
  sars                   NUMBER                    -- from Currency
  , CONSTRAINT pk_amlh PRIMARY KEY (no)
);

-- ────────────────────────────────────────────────────────────────
-- Mkb2  (inferred from DTO: plocation)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE Mkb2 (
  NOM                    NUMBER(10,0)    NOT NULL  -- from (synthesised PK — not projected by any DTO; inferred from SQL JOIN patterns),
  num                    VARCHAR2(255)             -- from plocation,
  name                   VARCHAR2(255)             -- from plocation,
  no_mstlm               VARCHAR2(255)             -- from plocation,
  red                    VARCHAR2(255)             -- from plocation,
  sdad                   VARCHAR2(255)             -- from plocation,
  GetListGroup           VARCHAR2(255)             -- from plocation
  , CONSTRAINT pk_mkb2 PRIMARY KEY (NOM)
);

-- ────────────────────────────────────────────────────────────────
-- DATA_D  (inferred from DTOs: AccountsLedger, ItemBonds)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE DATA_D (
  NOMS                   NUMBER(10,0)    NOT NULL  -- from (synthesised PK — not projected by any DTO; inferred from SQL JOIN patterns),
  Type                   NUMBER(10,0)              -- from AccountsLedger, ItemBonds,
  Notes                  VARCHAR2(255)             -- from AccountsLedger, ItemBonds,
  Num                    VARCHAR2(255)             -- from AccountsLedger, ItemBonds,
  Mden                   NUMBER                    -- from AccountsLedger, ItemBonds,
  Dain                   NUMBER                    -- from AccountsLedger, ItemBonds,
  Balance                NUMBER                    -- from AccountsLedger, ItemBonds,
  MDate                  VARCHAR2(255)             -- from AccountsLedger, ItemBonds,
  Pnum                   VARCHAR2(255)             -- from AccountsLedger,
  Nref                   VARCHAR2(255)             -- from AccountsLedger,
  name                   VARCHAR2(255)             -- from ItemBonds,
  name_s                 VARCHAR2(255)             -- from ItemBonds,
  nmstnd                 VARCHAR2(255)             -- from ItemBonds,
  notes2                 VARCHAR2(255)             -- from ItemBonds,
  num_s                  VARCHAR2(255)             -- from ItemBonds,
  price_trans            NUMBER                    -- from ItemBonds,
  notes_box              VARCHAR2(255)             -- from ItemBonds,
  cas                    VARCHAR2(255)             -- from ItemBonds,
  currencyid             VARCHAR2(255)             -- from ItemBonds,
  currencyname           VARCHAR2(255)             -- from ItemBonds,
  currency               VARCHAR2(255)             -- from ItemBonds,
  account                VARCHAR2(255)             -- from ItemBonds
  , CONSTRAINT pk_data_d PRIMARY KEY (NOMS)
);

-- ────────────────────────────────────────────────────────────────
-- DATA_M  (inferred from DTO: ItemReading)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE DATA_M (
  NOMS                   NUMBER(10,0)    NOT NULL  -- from (synthesised PK — not projected by any DTO; inferred from SQL JOIN patterns),
  name                   VARCHAR2(255)             -- from ItemReading,
  namet                  VARCHAR2(255)             -- from ItemReading,
  notblh                 VARCHAR2(255)             -- from ItemReading,
  ind                    VARCHAR2(255)             -- from ItemReading,
  nomstlm                VARCHAR2(255)             -- from ItemReading,
  noadad                 VARCHAR2(255)             -- from ItemReading,
  num                    VARCHAR2(255)             -- from ItemReading,
  nog                    VARCHAR2(255)             -- from ItemReading,
  ks                     VARCHAR2(255)             -- from ItemReading,
  kh                     VARCHAR2(255)             -- from ItemReading,
  cas                    VARCHAR2(255)             -- from ItemReading,
  asts                   VARCHAR2(255)             -- from ItemReading,
  sk                     VARCHAR2(255)             -- from ItemReading,
  mt                     VARCHAR2(255)             -- from ItemReading,
  kmsn                   VARCHAR2(255)             -- from ItemReading,
  matm33                 VARCHAR2(255)             -- from ItemReading,
  rtrdn                  VARCHAR2(255)             -- from ItemReading
  , CONSTRAINT pk_data_m PRIMARY KEY (NOMS)
);

-- ────────────────────────────────────────────────────────────────
-- SNDK_A  (inferred from DTOs: RepBoxMovesDetals, RepBoxMoves)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE SNDK_A (
  NOS                    NUMBER(10,0)    NOT NULL  -- from (synthesised PK — not projected by any DTO; inferred from SQL JOIN patterns),
  name                   VARCHAR2(255)             -- from RepBoxMovesDetals, RepBoxMoves,
  typems                 VARCHAR2(255)             -- from RepBoxMovesDetals,
  nmstnd                 VARCHAR2(255)             -- from RepBoxMovesDetals,
  notes                  VARCHAR2(255)             -- from RepBoxMovesDetals,
  amount                 VARCHAR2(255)             -- from RepBoxMovesDetals,
  num                    VARCHAR2(255)             -- from RepBoxMoves,
  balance                VARCHAR2(255)             -- from RepBoxMoves,
  mden                   VARCHAR2(255)             -- from RepBoxMoves,
  dain                   VARCHAR2(255)             -- from RepBoxMoves,
  fbalance               VARCHAR2(255)             -- from RepBoxMoves
  , CONSTRAINT pk_sndk_a PRIMARY KEY (NOS)
);

-- ────────────────────────────────────────────────────────────────
-- titl  (inferred from DTO: CompanyInfo)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE titl (
  compname               VARCHAR2(255)             -- from CompanyInfo,
  compaddress            VARCHAR2(255)             -- from CompanyInfo,
  compactive             VARCHAR2(255)             -- from CompanyInfo,
  comptelephone          VARCHAR2(255)             -- from CompanyInfo
);

-- ────────────────────────────────────────────────────────────────
-- Suggested indexes (inferred from WHERE/JOIN patterns in #US)
-- ────────────────────────────────────────────────────────────────
-- 1. USER_R(NAME_U) — auth lookup at #US +0x4c7a `select * from USER_R where NAME_U='`
--   CREATE INDEX idx_user_r_1 ON USER_R (NAME_U);
-- 2. USER_MNATK(NOU) — per-user enumeration at #US +0xebf, +0x18ac
--   CREATE INDEX idx_user_mnatk_2 ON USER_MNATK (NOU);
-- 3. USER_MNATK(no_mstlm) — joined to Mkb2.NOM at #US +0x14cf
--   CREATE INDEX idx_user_mnatk_3 ON USER_MNATK (no_mstlm);
-- 4. data_acc(NOA) — joined to SNDK_A/SNDS_A at #US +0x2063, +0x2d1d
--   CREATE INDEX idx_data_acc_4 ON data_acc (NOA);
-- 5. data_acc(no_mstlm) — filter at #US +0x3132
--   CREATE INDEX idx_data_acc_5 ON data_acc (no_mstlm);
-- 6. DATA_D(NOA, DATES) — ledger time-range queries at #US +0x42f8
--   CREATE INDEX idx_data_d_6 ON DATA_D (NOA, DATES);
-- 7. SNDK_A(no_box, DATES) — box-movement reports at #US +0x2063
--   CREATE INDEX idx_sndk_a_7 ON SNDK_A (no_box, DATES);
-- 8. SNDS_A(no_box, DATES) — box-movement reports at #US +0x2246
--   CREATE INDEX idx_snds_a_8 ON SNDS_A (no_box, DATES);

-- ────────────────────────────────────────────────────────────────
-- Suggested foreign keys (inferred from JOIN patterns in #US)
-- ────────────────────────────────────────────────────────────────
-- SNDK_A.no_box → USER_R.NOA  (#US +0x2063)
--   ALTER TABLE SNDK_A ADD CONSTRAINT fk_sndk_a_no_box FOREIGN KEY (no_box) REFERENCES USER_R(NOA);
-- SNDS_A.no_box → USER_R.NOA  (#US +0x2246)
--   ALTER TABLE SNDS_A ADD CONSTRAINT fk_snds_a_no_box FOREIGN KEY (no_box) REFERENCES USER_R(NOA);
-- SNDK_A.NOA → data_acc.NOA  (#US +0x2d1d)
--   ALTER TABLE SNDK_A ADD CONSTRAINT fk_sndk_a_noa FOREIGN KEY (NOA) REFERENCES data_acc(NOA);
-- SNDS_A.NOA → data_acc.NOA  (#US +0x337e)
--   ALTER TABLE SNDS_A ADD CONSTRAINT fk_snds_a_noa FOREIGN KEY (NOA) REFERENCES data_acc(NOA);
-- SNDK_A.NOAML → amlh.no  (#US +0x252a)
--   ALTER TABLE SNDK_A ADD CONSTRAINT fk_sndk_a_noaml FOREIGN KEY (NOAML) REFERENCES amlh(no);
-- SNDS_A.NOAML → amlh.no  (#US +0x337e)
--   ALTER TABLE SNDS_A ADD CONSTRAINT fk_snds_a_noaml FOREIGN KEY (NOAML) REFERENCES amlh(no);
-- USER_MNATK.no_mstlm → Mkb2.NOM  (#US +0x1578)
--   ALTER TABLE USER_MNATK ADD CONSTRAINT fk_user_mnatk_no_mstlm FOREIGN KEY (no_mstlm) REFERENCES Mkb2(NOM);
-- USER_MNATK.NOU → USER_R.NOU  (#US +0xebf)
--   ALTER TABLE USER_MNATK ADD CONSTRAINT fk_user_mnatk_nou FOREIGN KEY (NOU) REFERENCES USER_R(NOU);
-- data_acc.no_mstlm → Mkb2.NOM  (#US +0x3132)
--   ALTER TABLE data_acc ADD CONSTRAINT fk_data_acc_no_mstlm FOREIGN KEY (no_mstlm) REFERENCES Mkb2(NOM);
-- DATA_D.NOA → data_acc.NOA  (#US +0x42f8)
--   ALTER TABLE DATA_D ADD CONSTRAINT fk_data_d_noa FOREIGN KEY (NOA) REFERENCES data_acc(NOA);
