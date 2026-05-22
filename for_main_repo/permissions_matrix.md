# Permissions Matrix — `app1` (React Native)

> Source: `analysis/04_PERMISSIONS_SYSTEM.md` (Phase 6, aggregate 86 % confidence).
> This file is intentionally short and **directly copy-able** into the RN repo.

---

## TL;DR

The user-permission model has **two tiers**:

| Tier | Where it lives                 | What it gates                                                        |
|------|--------------------------------|----------------------------------------------------------------------|
| A    | `USER_R` row (7 `Int32` flags) | *Whether* a user can perform an action (edit / delete / save / read / report / admin) |
| B    | `USER_MNATK` junction (per place) | *Which places* the user can read or write on                       |

The RN client **mirrors** Tier-A from the `Users` object returned by `Login` to gate
UI elements. **Tier-B is server-enforced and transparent** — the client just renders
the data the gateway returns.

---

## 1. Tier-A — the 7 flags from `Users`

Source of truth: the `Users` DTO from `/Login` (see `for_main_repo/dtos.ts`).

| Field          | Semantic                              | Boolean coercion         | UI gates (RN)                                                                                                  |
|----------------|---------------------------------------|--------------------------|----------------------------------------------------------------------------------------------------------------|
| `Users.NOA`    | Accounts access + own till account-id | `NOA > 0`                | Show "Accounts" tab; navigation to `AccountsListScreen`                                                       |
| `Users.ED`     | Edit existing records                 | `ED === 1`               | Enable edit button on bonds (`BondDetailScreen`), readings (`ReadingDetailScreen`)                            |
| `Users.DE`     | Delete records                        | `DE === 1`               | Enable delete button on bonds / payment bonds                                                                  |
| `Users.S_K`    | Save kara'a (reading) — new           | `S_K === 1`              | Show "+" FAB on `ReadingsScreen`; enable `SaveReading` form submit                                            |
| `Users.S_S`    | Save sanad (bond) — new               | `S_S === 1`              | Show "+" FAB on `BondsScreen`; enable `SaveBond` / `SaveBondPayment` form submits                             |
| `Users.REP`    | Reports access                        | `REP === 1`              | Show "Reports" tab; navigation to all `GetRep*` report screens                                                |
| `Users.SYS`    | System admin                          | `SYS === 1`              | Show "Users management", "Reset password", and a "system" hidden menu. Also enables `Authenticate` as another user. |

> **Important**: never trust these flags client-side beyond UI gating. The gateway
> independently re-checks every action. The flags are *cosmetic*; the gateway is the
> source of truth.

### TypeScript helper (drop into `app1/src/auth/permissions.ts`)

```ts
import type { Users } from './dtos';

export type Permission =
  | 'view_accounts'
  | 'edit'
  | 'delete'
  | 'save_reading'
  | 'save_bond'
  | 'view_reports'
  | 'sys_admin';

export const can = (me: Users | null, p: Permission): boolean => {
  if (!me) return false;
  switch (p) {
    case 'view_accounts': return me.NOA > 0;
    case 'edit':          return me.ED === 1;
    case 'delete':        return me.DE === 1;
    case 'save_reading':  return me.S_K === 1;
    case 'save_bond':     return me.S_S === 1;
    case 'view_reports':  return me.REP === 1;
    case 'sys_admin':     return me.SYS === 1;
  }
};

// Usage in components:
//   const canDelete = can(me, 'delete');
//   <Button disabled={!canDelete} onPress={onDeleteBond}>Delete</Button>
```

---

## 2. Tier-A → endpoint map (so you know what 403 means)

If a 403 (or `ServiceFault.error_no=403`) comes back from one of these endpoints,
the *first* thing to check is the corresponding flag:

| Endpoint                          | Required flag |
|-----------------------------------|---------------|
| `GetListAccounts`                 | `NOA`         |
| `GetListAccountsLedger`           | `NOA`         |
| `GetAccountBalance`               | `NOA`         |
| `GetAccountBalanceInfo`           | `NOA`         |
| `GetListBonds`                    | `NOA`         |
| `GetListBondsElect`               | `NOA`         |
| `GetListBondsPayment`             | `NOA`         |
| `UpdateBond`                      | `ED`          |
| `UpdateBondPayment`               | `ED`          |
| `UpdateReading`                   | `ED` and `S_K`|
| `UpdateAllReading`                | `ED` and `S_K`|
| `DeleteBond`                      | `DE`          |
| `DeleteBondPayment`               | `DE`          |
| `SaveBond`                        | `S_S`         |
| `SaveBondPayment`                 | `S_S`         |
| `GetRepBalanceDetails`            | `REP`         |
| `GetRepBalanceDetailsByDate`      | `REP`         |
| `GetRepBalanceHeader`             | `REP`         |
| `GetRepBalanceHeaderElect`        | `REP`         |
| `GetRepBalanceOpen`               | `REP`         |
| `GetRepBondsHeader`               | `REP`         |
| `GetRepBondsHeaderElectric`       | `REP`         |
| `GetRepBoxMove`                   | `REP`         |
| `GetRepBoxMoveDetails`            | `REP`         |
| `GetRepExpenses`                  | `REP`         |
| `GetRepReadingHeader`             | `REP`         |
| `GetFinalBalance`                 | `REP`         |
| `ResetPassword`                   | `SYS`         |
| `GetListUsers`                    | `SYS`         |
| `Authenticate` (as other user)    | `SYS`         |

> Confidence on this mapping: **80 %** (inferred from flag naming + endpoint
> semantics + the `GetRep*` family clearly matching `REP`).

---

## 3. Tier-B — per-place ACL (transparent to RN)

The gateway enforces `USER_MNATK` filtering on every account/place query. The RN
client does not need to do anything — *but* it can fetch `GetListUserPlaces` to
populate a place-selector UI element if you want users to see what they have
access to.

### `UserPlaces` shape (already in `for_main_repo/dtos.ts`)

```ts
export interface UserPlaces {
  NOU?:       number;
  no_mstlm?:  number;
  RED?:       number;   // 1 = read allowed
  SDAD?:      number;   // 1 = write allowed
  NAMEM?:     string;   // display name (Arabic)
}
```

### Picking the right places to render

```ts
const readablePlaces = userPlaces.filter(p => (p.RED ?? 0) > 0);
const writablePlaces = userPlaces.filter(p => (p.SDAD ?? 0) > 0);
```

> If a user's `USER_MNATK` rows are empty, the gateway returns empty result sets
> for `GetListAccounts*` even if Tier-A `NOA > 0`. Surface a helpful empty-state.

---

## 4. End-to-end gating pattern (recommended)

```tsx
import { can } from '../auth/permissions';
import { useMe } from '../auth/useMe';

export const BondActions = ({ bond }: { bond: ItemBonds }) => {
  const me = useMe();
  return (
    <>
      <Button disabled={!can(me, 'edit')}   onPress={() => onEdit(bond)}>تعديل</Button>
      <Button disabled={!can(me, 'delete')} onPress={() => onDelete(bond)}>حذف</Button>
    </>
  );
};
```

The gateway will still 403 if the user lies about their token; the UI gate is
just to keep impossible actions out of the user's face.

---

## 5. Open questions for app1

1. The exact `error_no` values returned for Tier-A failures are not yet captured
   from a live server — recommended to default-handle on `ServiceFault.error_no >= 403`
   plus an Arabic-language toast.
2. The `SYS` flag is treated as a Tier-B short-circuit in `04_PERMISSIONS_SYSTEM.md`
   §6; confirm with a live capture against a `SYS=1` account.

— end of `permissions_matrix.md` —
