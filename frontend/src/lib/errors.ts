const BACKEND_ERROR_MAP: Record<string, string> = {
	'Email already registered': 'error.emailAlreadyRegistered',
	'User not found': 'error.userNotFound',
	'Cannot change your own admin role': 'error.cannotChangeOwnRole',
};

export function localizeBackendError(err: unknown): string {
	if (err instanceof Error) {
		if (err.message.startsWith('error.')) {
			return err.message;
		}
		const mappedKey = BACKEND_ERROR_MAP[err.message];
		if (mappedKey) {
			return mappedKey;
		}
		return err.message;
	}
	return 'Unknown error';
}

export function localizeError(err: unknown, translate: (key: string) => string, fallback: string): string {
	const localized = localizeBackendError(err);
	if (localized.startsWith('error.')) {
		return translate(localized);
	}
	if (localized !== 'Unknown error') {
		return localized;
	}
	return fallback;
}

export function shouldShowActionToast(message: string): boolean {
	return message !== 'Missing API key' && message !== 'Not authenticated';
}
