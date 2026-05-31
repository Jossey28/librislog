<script lang="ts">
	import { version, gitSha } from '$lib/version';

	const knownSha = gitSha && gitSha !== 'unknown';
	const isPreRelease = version.includes('-');

	const displayVersion = knownSha && isPreRelease
		? `${version}+${gitSha.slice(0, 7)}`
		: version;

	const href = knownSha && isPreRelease
		? `https://github.com/codebude/librislog/commit/${gitSha}`
		: knownSha
			? `https://github.com/codebude/librislog/releases/tag/${version}`
			: null;
</script>

{#if href}
	<a {href} target="_blank" rel="noopener noreferrer" class="hover:underline">{displayVersion}</a>
{:else}
	{displayVersion}
{/if}
