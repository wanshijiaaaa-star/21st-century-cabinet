<template>
  <span class="text-icon">
    <i :class="iconClass"></i>
    <canvas ref="canvas" class="text-icon-canvas"></canvas>
  </span>
</template>

<script>
export default {
  name: 'TextIcon',
  props: {
    text: {
      type: String,
      required: true
    },
    iconClass: {
      type: String,
      required: true
    },
    backgroundColor: {
      type: String,
      default: '#fff'
    },
    textColor: {
      type: String,
      default: '#ff0000'
    }
  },
  mounted() {
    const canvas = this.$refs.canvas;
    const ctx = canvas.getContext('2d');
    const letter = this.text.charAt(0).toUpperCase();
    
    // 设置画布大小
    canvas.width = 24;
    canvas.height = 24;
    
    // 绘制背景
    ctx.fillStyle = this.backgroundColor;
    ctx.beginPath();
    ctx.arc(12, 12, 10, 0, Math.PI * 2);
    ctx.fill();
    
    // 绘制字母
    ctx.fillStyle = this.textColor;
    ctx.font = 'bold 14px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(letter, 12, 12);
  }
};
</script>

<style scoped>
.text-icon {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.text-icon-canvas {
  width: 24px;
  height: 24px;
  border-radius: 50%;
}
</style>