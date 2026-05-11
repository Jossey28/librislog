export function toDateInputValue(value: string | null | undefined): string {
	if (!value) return '';
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return '';
	return date.toISOString().slice(0, 10);
}

export function fromDateInputValue(value: string): string | null {
	const trimmed = value.trim();
	if (!trimmed) return null;
	return `${trimmed}T00:00:00.000Z`;
}

export function formatDate(value: string | null | undefined): string {
	if (!value) return '';
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return '';
	return date.toISOString().slice(0, 10);
}
