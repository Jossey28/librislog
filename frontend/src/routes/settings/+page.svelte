<script lang="ts">
	import { _, locale, setLocale, SUPPORTED_LOCALES, type AppLocale } from '$lib/i18n';

	function onLocaleChange(event: Event) {
		const next = (event.currentTarget as HTMLSelectElement).value as AppLocale;
		if (!SUPPORTED_LOCALES.includes(next)) return;
		setLocale(next);
	}
</script>

<div class="max-w-2xl mx-auto flex flex-col gap-6">
	<div>
		<h1 class="text-2xl font-bold">{$_('settings.title')}</h1>
		<p class="text-sm text-base-content/70 mt-1">{$_('settings.languageHelp')}</p>
	</div>

	<div class="card bg-base-100 shadow-sm border border-base-200">
		<div class="card-body gap-3">
			<label class="form-control">
				<span class="label label-text">{$_('settings.languageTitle')}</span>
				<select class="select select-bordered" value={$locale} onchange={onLocaleChange}>
					{#each SUPPORTED_LOCALES as code}
						<option value={code}>{$_(`languages.${code}`)}</option>
					{/each}
				</select>
			</label>
			<p class="text-xs text-base-content/60">{$_('settings.saved')}</p>
		</div>
	</div>
</div>
