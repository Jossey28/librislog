<script lang="ts">
	let {
		sourceFields,
		dbFields,
		mapping,
		onChange
	}: {
		sourceFields: string[];
		dbFields: string[];
		mapping: Record<string, string>;
		onChange: (mapping: Record<string, string>) => void;
	} = $props();

	const MANDATORY_FIELDS = ['title', 'author', 'page_count'];

	function update(target: string, source: string) {
		const next = { ...mapping };
		// Remove any existing mapping that uses this source (enforce: one source per target)
		for (const [t, s] of Object.entries(next)) {
			if (s === source) {
				delete next[t];
			}
		}
		if (source) {
			next[target] = source;
		} else {
			delete next[target];
		}
		onChange(next);
	}
</script>

<div class="grid gap-2">
	{#each dbFields as dbField}
		{@const isMandatory = MANDATORY_FIELDS.includes(dbField)}
		{@const currentSource = mapping[dbField] ?? ''}
		<div class="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-2 items-center border border-base-200 rounded-lg p-2 {isMandatory && !currentSource ? 'bg-error/5 border-error/30' : ''}">
			<div class="text-sm break-all">
				<span class="font-medium">{dbField}</span>
				{#if isMandatory}
					<span class="text-error text-xs ml-1">*</span>
				{/if}
			</div>
			<div class="text-base-content/50 text-center">&lt;-</div>
			<select
				class="select select-bordered select-sm {isMandatory && !currentSource ? 'select-error' : ''}"
				name={`mapping-target-${dbField}`}
				aria-label={`Map source for ${dbField}`}
				value={currentSource}
				onchange={(e) => update(dbField, e.currentTarget.value)}
			>
				<option value="">(none)</option>
				{#each sourceFields as source}
					<option value={source}>{source}</option>
				{/each}
			</select>
		</div>
	{/each}
</div>

<div class="text-xs text-base-content/50 mt-1">
	<span class="text-error">*</span> = required field
</div>
