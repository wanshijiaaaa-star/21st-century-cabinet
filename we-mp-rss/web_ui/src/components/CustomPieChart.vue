<template>
  <div class="pie-chart-container">
    <svg :width="size" :height="size" viewBox="0 0 100 100">
      <circle
        cx="50"
        cy="50"
        r="40"
        fill="none"
        stroke="#f0f0f0"
        stroke-width="3"
      />
      <circle
        cx="50"
        cy="50"
        r="40"
        fill="none"
        :stroke="getStrokeColor"
        stroke-width="5"
        :stroke-dasharray="dashArray"
        stroke-linecap="round"
        transform="rotate(-90 50 50)"
      />
      <text x="50" y="30" text-anchor="middle" dominant-baseline="middle" font-size="12" fill="#333">
        {{ title }}
      </text>
      <text x="50" y="50" text-anchor="middle" dominant-baseline="middle" font-size="18" :fill="getStrokeColor" font-weight="bold">
        {{ percent }}%
      </text>
      <text x="50" y="70" text-anchor="middle" dominant-baseline="middle" font-size="6" fill="#666">
        {{ info }}
      </text>
    </svg>
  </div>
</template>

<script>
export default {
  props: {
    percent: {
      type: Number,
      default: 0
    },
    size: {
      type: Number,
      default: 150
    },
    title: {
      type: String,
      default: ""
    },
    info: {
      type: String,
      default: ""
    }
  },
  computed: {
    dashArray() {
      const circumference = 2 * Math.PI * 40;
      const progress = (this.percent / 100) * circumference;
      return `${progress} ${circumference}`;
    },
    getStrokeColor() {
      const startColor = { r: 32, g: 165, b: 58 };
      const endColor = { r: 245, g: 34, b: 45 };
      const ratio = this.percent / 100;
      const r = Math.floor(startColor.r + (endColor.r - startColor.r) * ratio);
      const g = Math.floor(startColor.g + (endColor.g - startColor.g) * ratio);
      const b = Math.floor(startColor.b + (endColor.b - startColor.b) * ratio);
      return `rgb(${r}, ${g}, ${b})`;
    }
  }
};
</script>

<style scoped>
.pie-chart-container {
  display: inline-block;
}
</style>