import { addMessages, init, locale, register, waitLocale, _ } from 'svelte-i18n';

export const SUPPORTED_LOCALES = ['en', 'de'] as const;
export type AppLocale = (typeof SUPPORTED_LOCALES)[number];

const DEFAULT_LOCALE: AppLocale = 'en';
const STORAGE_KEY = 'librislog.locale';

const envLocale = (import.meta.env.PUBLIC_DEFAULT_LOCALE as string | undefined)?.toLowerCase();
const configuredDefaultLocale: AppLocale = isSupportedLocale(envLocale) ? envLocale : DEFAULT_LOCALE;

register('en', () => import('./locales/en.json'));
register('de', () => import('./locales/de.json'));

addMessages('en', {});

let initialized = false;

function isSupportedLocale(value: string | null | undefined): value is AppLocale {
	return !!value && (SUPPORTED_LOCALES as readonly string[]).includes(value);
}

function getStoredLocale(): AppLocale | null {
	if (typeof localStorage === 'undefined') return null;
	const stored = localStorage.getItem(STORAGE_KEY)?.toLowerCase() ?? null;
	return isSupportedLocale(stored) ? stored : null;
}

export async function setupI18n() {
	if (initialized) {
		await waitLocale();
		return;
	}

	const initialLocale = getStoredLocale() ?? configuredDefaultLocale;

	init({
		fallbackLocale: 'en',
		initialLocale
	});

	if (typeof localStorage !== 'undefined') {
		locale.subscribe((value) => {
			if (!isSupportedLocale(value)) return;
			localStorage.setItem(STORAGE_KEY, value);
		});
	}

	initialized = true;
	await waitLocale();
}

export function setLocale(nextLocale: AppLocale) {
	locale.set(nextLocale);
}

export function getConfiguredDefaultLocale() {
	return configuredDefaultLocale;
}

export { _, locale };
