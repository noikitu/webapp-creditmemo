import type { Component } from 'vue';

export interface MenuItem {
  title: string;
  name: string;
  icon?: Component;
  isActive: boolean;
}
