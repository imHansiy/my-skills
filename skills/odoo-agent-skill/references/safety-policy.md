# Odoo Mutation Safety Policy

## General

- Read before write.
- Prefer dry-run.
- Mutate only exact IDs.
- Snapshot before execution.
- Show a diff before asking the user to approve.

## Update restrictions

- Do not update protected models by default.
- Do not update protected fields by default.
- Do not update more than 20 records per command without explicit bulk approval.
- Use quiet mail context for bulk changes where chatter/email side effects are not desired.

## Delete restrictions

- Prefer archive/deactivate over unlink.
- Never delete accounting, stock, company, user, security, payment, or configuration records without exceptional explicit instruction.
- Never delete from fuzzy search results.
- Always snapshot first.

## Protected model prefixes

- account.
- stock.
- payment.
- ir.

## Protected models

- res.users
- res.company
- account.move
- account.move.line
- stock.picking
- stock.move
- stock.quant
- ir.config_parameter
- ir.model.access
- ir.rule
- ir.module.module

## Protected field keywords

- password
- token
- secret
- key
- credential
