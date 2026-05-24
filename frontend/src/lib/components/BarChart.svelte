<script lang="ts">
	import '$lib/chartjs/register';
	import { Bar } from 'svelte-chartjs';
	import { getDaisyColorRgb } from '$lib/chartjs/theme';
	import { themeApplyCount } from '$lib/stores/theme';
	import { onMount } from 'svelte';
	import type { Chart as ChartJS, ChartData, ChartOptions } from 'chart.js';

	let {
		labels = [],
		data = [],
		label = '',
		color = 'primary',
		emptyText = 'No data',
		height = 200,
		onChart = (_chart: ChartJS<'bar'>) => {},
	}: {
		labels: string[];
		data: number[];
		label: string;
		color: string;
		emptyText?: string;
		height?: number;
		onChart?: (chart: ChartJS<'bar'>) => void;
	} = $props();

	let chart = $state<ChartJS<'bar'> | null>(null);
	let _themeSignal = $state(0);

	$effect(() => {
		if (chart) {
			onChart(chart);
		}
	});

	onMount(() => {
		return themeApplyCount.subscribe((n: number) => {
			_themeSignal = n;
		});
	});

	const chartData = $derived.by<ChartData<'bar'>>(() => {
		void _themeSignal;
		return {
			labels,
			datasets: [
				{
					label,
					data,
					backgroundColor: getDaisyColorRgb(color),
					borderColor: 'transparent',
					borderWidth: 0,
					borderRadius: 4,
					barPercentage: 0.7,
				},
			],
		};
	});

	const options = $derived.by<ChartOptions<'bar'>>(() => {
		void _themeSignal;
		return {
			responsive: true,
			maintainAspectRatio: false,
			animation: { duration: 0 },
			plugins: {
				legend: { display: false },
				tooltip: {
					enabled: true,
					mode: 'index' as const,
					intersect: false,
				},
				zoom: {
					pan: {
						enabled: true,
						mode: 'x' as const,
					},
					zoom: {
						wheel: { enabled: true },
						pinch: { enabled: true },
						mode: 'x' as const,
					},
				},
			},
			scales: {
				x: {
					grid: { display: false },
					ticks: {
						maxRotation: 45,
						minRotation: 45,
						autoSkip: true,
						color: getDaisyColorRgb('base-content'),
					},
				},
				y: {
					beginAtZero: true,
					grid: {
						color: getDaisyColorRgb('base-200'),
					},
					ticks: {
						color: getDaisyColorRgb('base-content'),
					},
				},
			},
		};
	});

</script>

{#if data.length === 0}
	<div class="flex items-center justify-center h-40 text-base-content/50">
		<p>{emptyText}</p>
	</div>
{:else}
	<div role="img" aria-label={label} class="relative select-none" style="height: {height}px">
		<Bar bind:chart={chart} data={chartData} {options} />
	</div>
{/if}
