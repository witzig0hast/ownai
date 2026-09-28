"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as contactsApi from "@/lib/api/contacts";
import type { Contact } from "@/lib/types";

const MONTH_NAMES = [
  "Januar", "Februar", "März", "April", "Mai", "Juni",
  "Juli", "August", "September", "Oktober", "November", "Dezember",
];

function formatBirthday(contact: Contact): string | null {
  if (contact.birthday_month == null || contact.birthday_day == null) return null;
  const monthName = MONTH_NAMES[contact.birthday_month - 1];
  const yearSuffix = contact.birthday_year != null ? ` ${contact.birthday_year}` : "";
  return `${contact.birthday_day}. ${monthName}${yearSuffix}`;
}

export function ContactsTab() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [birthdayDay, setBirthdayDay] = useState("");
  const [birthdayMonth, setBirthdayMonth] = useState("");
  const [birthdayYear, setBirthdayYear] = useState("");
  const [notes, setNotes] = useState("");
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    contactsApi
      .listContacts()
      .then(setContacts)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Laden fehlgeschlagen."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void (async () => {
      load();
    })();
  }, [load]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await contactsApi.createContact({
        name: name.trim(),
        phone: phone.trim() || null,
        email: email.trim() || null,
        birthday_day: birthdayDay ? Number(birthdayDay) : null,
        birthday_month: birthdayMonth ? Number(birthdayMonth) : null,
        birthday_year: birthdayYear ? Number(birthdayYear) : null,
        notes: notes.trim() || null,
      });
      setName("");
      setPhone("");
      setEmail("");
      setBirthdayDay("");
      setBirthdayMonth("");
      setBirthdayYear("");
      setNotes("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Hinzufügen fehlgeschlagen.");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await contactsApi.deleteContact(id);
      setContacts((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.");
    }
  }

  return (
    <div className="max-w-xl">
      <p className="mb-4 text-sm text-zinc-500">
        Kontakte, die sich der Assistent merkt. Ist ein Geburtstag hinterlegt, erinnert er dich am Tag
        selbst automatisch per Push-Benachrichtigung daran.
      </p>

      <form onSubmit={handleAdd} className="mb-4 flex flex-col gap-2 rounded-2xl border border-zinc-200 p-3 dark:border-zinc-800">
        <input
          type="text"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Telefon"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="flex-1 rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
          />
          <input
            type="email"
            placeholder="E-Mail"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="flex-1 rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Geburtstag:</span>
          <input
            type="number"
            min={1}
            max={31}
            placeholder="Tag"
            value={birthdayDay}
            onChange={(e) => setBirthdayDay(e.target.value)}
            className="w-16 rounded-xl border border-zinc-300 px-2 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
          <input
            type="number"
            min={1}
            max={12}
            placeholder="Monat"
            value={birthdayMonth}
            onChange={(e) => setBirthdayMonth(e.target.value)}
            className="w-20 rounded-xl border border-zinc-300 px-2 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
          <input
            type="number"
            min={1900}
            max={2100}
            placeholder="Jahr (optional)"
            value={birthdayYear}
            onChange={(e) => setBirthdayYear(e.target.value)}
            className="w-28 rounded-xl border border-zinc-300 px-2 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
        </div>
        <input
          type="text"
          placeholder="Notizen (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={adding || !name.trim()}
          className="self-start rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:scale-[1.03] hover:bg-zinc-700 hover:shadow active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Kontakt hinzufügen
        </button>
      </form>

      <ErrorMessage message={error} />

      {loading ? (
        <p className="text-sm text-zinc-500">Lade...</p>
      ) : contacts.length === 0 ? (
        <p className="text-sm text-zinc-500">Noch keine Kontakte.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 rounded-2xl border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {contacts.map((c, i) => {
            const birthday = formatBirthday(c);
            return (
              <li
                key={c.id}
                className="animate-fade-in-up flex items-center justify-between gap-3 px-3 py-2 text-sm transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900/60"
                style={{ animationDelay: `${Math.min(i, 10) * 30}ms` }}
              >
                <div>
                  <p className="text-zinc-900 dark:text-zinc-100">{c.name}</p>
                  <p className="text-xs text-zinc-400">
                    {[c.phone, c.email, birthday ? `🎂 ${birthday}` : null].filter(Boolean).join(" · ") || "—"}
                  </p>
                  {c.notes && <p className="mt-0.5 text-xs text-zinc-500">{c.notes}</p>}
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(c.id)}
                  className="shrink-0 rounded-full px-2 py-1 text-xs text-red-500 transition-all hover:scale-105 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950/40"
                >
                  Löschen
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
