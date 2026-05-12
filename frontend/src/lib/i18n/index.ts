import { addMessages, init, locale, register, waitLocale, _ } from 'svelte-i18n';
import { api } from '$lib/api';

export const SUPPORTED_LOCALES = ['en', 'de'] as const;
export type AppLocale = (typeof SUPPORTED_LOCALES)[number];

const DEFAULT_LOCALE: AppLocale = 'en';

const envLocale = (import.meta.env.PUBLIC_DEFAULT_LOCALE as string | undefined)?.toLowerCase();
const configuredDefaultLocale: AppLocale = isSupportedLocale(envLocale) ? envLocale : DEFAULT_LOCALE;

register('en', () => import('./locales/en.json'));
register('de', () => import('./locales/de.json'));

addMessages('en', {});

let initialized = false;

function isSupportedLocale(value: string | null | undefined): value is AppLocale {
	return !!value && (SUPPORTED_LOCALES as readonly string[]).includes(value);
}

export async function setupI18n() {
	if (initialized) {
		await waitLocale();
		return;
	}

	let initialLocale = configuredDefaultLocale;
	try {
		const settings = await api.profile.getSettings();
		if (isSupportedLocale(settings.language)) {
			initialLocale = settings.language;
		}
	} catch {
		// unauthenticated route before cookie-based login
	}

	init({
		fallbackLocale: 'en',
		initialLocale
	});

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
