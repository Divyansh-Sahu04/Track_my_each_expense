# Spec: Delete Expense

## Overview
This step lets a logged-in user permanently remove one of their own expenses
via `/expenses/<id>/delete`. To avoid an irreversible action firing from a
single accidental click, the confirmation happens in-page: clicking the
delete icon opens a custom modal dialog on the profile page itself (title,
"this cannot be undone" text, and Cancel/Delete buttons), and only clicking
the modal's Delete button submits a `POST` that performs the actual
deletion — there is no separate confirmation page/route. The delete button
is a real `type="submit"` control inside its row's form, so if JavaScript
fails to load the click still submits the form directly (an unconfirmed but
functional delete) rather than becoming completely inert. Ownership is
enforced the same way as edit: a user can only delete expenses that belong
to them. One new query helper, `delete_expense`, is added to
`database/queries.py`. The transactions table in `profile.html` gains a red,
icon-only delete action to the right of the existing "Edit" action.

## Depends on
- Step 1: Database setup (`expenses` table exists with all required columns)
- Step 3: Login / Logout (`session["user_id"]` is set and enforced)
- Step 5: Profile page renders transactions (the delete action lives there)
- Step 7: Add Expense (establishes the form/validation pattern)
- Step 10: Edit Expense (establishes the ownership-scoped single-expense
  lookup pattern via `get_expense_by_id`)

## Routes
- `POST /expenses/<int:id>/delete` — delete the expense and redirect to
  `/profile` — logged-in only. No `GET` handler exists for this route; there
  is no standalone confirmation page.

## Database changes
No new tables or columns. All required columns already exist in `expenses`.

## Templates
- **Modify:** `templates/profile.html`
  - Replace the delete link with a `<form method="POST" action="{{ url_for('delete_expense', id=tx['id']) }}" data-delete-form>`
    per transaction row, positioned to the right of the existing "Edit" link
    inside the same `Actions` cell
  - Inside the form, an icon-only `<button type="submit" data-delete-trigger>`
    — no visible text label (a trash/bin icon), with
    `aria-label="Delete expense"` for accessibility
  - Styled red (using the existing `var(--danger)` CSS variable — never a
    hardcoded hex value) to visually signal a destructive action
  - A single shared modal (`[data-delete-modal]`, hidden by default) is
    rendered once on the page: a title, "this cannot be undone" text, and
    Cancel (`[data-delete-cancel]`) / Delete (`[data-delete-confirm]`)
    buttons

## Files to change
- `database/queries.py`
  - Add `delete_expense(expense_id, user_id)` — issues a parameterised
    `DELETE` scoped to both `id` and `user_id` for ownership safety
- `app.py`
  - Import `delete_expense` from `database.queries`
  - Replace the placeholder at `/expenses/<int:id>/delete` (currently
    returns the raw string `"Delete expense — coming in Step 9"`) with a
    `POST`-only handler:
    - Redirect to `/login` if not authenticated
    - Call `get_expense_by_id`; 404 if not found or not owned
    - Call `delete_expense`, flash a confirmation message, redirect to
      `/profile`
  - Route decorator: `@app.route("/expenses/<int:id>/delete", methods=["POST"])`
- `templates/profile.html`
  - Replace the icon-only delete `<a>` with a `<form data-delete-form>` +
    icon-only `<button type="submit" data-delete-trigger>` as described above
  - Add the shared `[data-delete-modal]` markup once on the page (not per row)
- `static/js/main.js`
  - Add a click listener on every `[data-delete-trigger]` button that calls
    `event.preventDefault()` (stopping the form's default submit) and opens
    the shared modal, remembering which row's form triggered it
  - The modal's Delete button (`[data-delete-confirm]`) submits that
    remembered form; its Cancel button (`[data-delete-cancel]`), clicking the
    overlay backdrop, or pressing Escape closes the modal without submitting
  - If this script fails to load or errors before the listener attaches, the
    button's native `type="submit"` still submits the form directly —
    an unconfirmed but functional fallback, not a dead control
- `static/css/profile.css`
  - `.delete-btn` styles the button (not an anchor): reset default button
    chrome (`border`, `background`, `font`, `cursor: pointer`) while keeping
    the same red/icon-only look as before
  - `.delete-form` keeps the wrapping form inline next to the Edit button
  - `.modal-overlay` / `.modal-card` / `.modal-title` / `.modal-text` /
    `.modal-actions` / `.btn-modal-cancel` / `.btn-modal-confirm` style the
    shared confirmation modal, all using existing CSS variables
  - `.modal-overlay[hidden] { display: none; }` is required alongside
    `.modal-overlay { display: flex; ... }` — an author-stylesheet rule
    setting `display` on the un-hidden class always outranks the browser's
    default `[hidden]` rule at equal specificity, so without this override
    the modal would never actually hide

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (unaffected by this step, listed per project
  convention)
- Foreign keys PRAGMA must be enabled on every connection (already done in
  `get_db()`)
- `delete_expense` must include `user_id = ?` in its `WHERE` clause as an
  ownership guard, in addition to `id = ?`
- Unauthenticated `POST` access must redirect to `/login`
- If the expense does not exist or belongs to another user, return a 404
- No `GET` handler for this route — a bare browser visit gets Flask's
  default 405, not a page
- After a successful delete, redirect to `url_for("profile")`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ — never £ or $
- Confirmation is a same-page custom modal dialog, not a navigation and not
  a native `window.confirm()` — vanilla JS only, no frameworks, following
  the pattern already used in `static/js/main.js`
- The delete button must remain a real `type="submit"` control so the
  feature degrades to a working (if unconfirmed) delete if JS fails, rather
  than becoming completely inert

## Definition of done
- [ ] Unauthenticated `POST /expenses/<id>/delete` redirects to `/login`
- [ ] `POST /expenses/<id>/delete` for a non-existent or other user's
      expense returns 404 and does not delete the row
- [ ] Clicking the delete icon on `/profile` opens the custom confirmation
      modal without navigating away from the page
- [ ] Cancelling the modal (Cancel button, backdrop click, or Escape) leaves
      the expense untouched
- [ ] Confirming the modal (Delete button) submits the form, deletes the
      expense, and redirects to `/profile`
- [ ] The deleted expense no longer appears in the profile transaction list
- [ ] Each row in the profile transaction table has a red, icon-only delete
      button (no text label) positioned to the right of the "Edit" link
- [ ] There is no separate delete confirmation page/route
