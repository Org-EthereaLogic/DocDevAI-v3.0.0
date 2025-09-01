/**
 * VirtualList - High-performance virtual scrolling component
 * 
 * Features:
 * - Renders only visible items
 * - Supports 10,000+ items
 * - Dynamic item heights
 * - Smooth scrolling
 * - Accessibility compliant
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import Box from '@mui/material/Box';
import { styled } from '@mui/material/styles';

interface VirtualListProps<T> {
  items: T[];
  itemHeight: number | ((index: number) => number);
  renderItem: (item: T, index: number) => React.ReactNode;
  height: number;
  width?: string | number;
  overscan?: number;
  onScroll?: (scrollTop: number) => void;
  className?: string;
  id?: string;
  'aria-label'?: string;
}

interface ItemPosition {
  index: number;
  offset: number;
  height: number;
}

const ScrollContainer = styled(Box)(({ theme }) => ({
  overflow: 'auto',
  position: 'relative',
  willChange: 'transform',
  '&::-webkit-scrollbar': {
    width: 8,
    height: 8
  },
  '&::-webkit-scrollbar-track': {
    backgroundColor: theme.palette.action.hover
  },
  '&::-webkit-scrollbar-thumb': {
    backgroundColor: theme.palette.action.disabled,
    borderRadius: 4,
    '&:hover': {
      backgroundColor: theme.palette.action.selected
    }
  }
}));

const ItemContainer = styled(Box)({
  position: 'absolute',
  top: 0,
  left: 0,
  width: '100%',
  willChange: 'transform'
});

/**
 * VirtualList component for rendering large datasets efficiently
 */
function VirtualList<T>({
  items,
  itemHeight,
  renderItem,
  height,
  width = '100%',
  overscan = 3,
  onScroll,
  className,
  id,
  'aria-label': ariaLabel
}: VirtualListProps<T>) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [isScrolling, setIsScrolling] = useState(false);
  const scrollTimeoutRef = useRef<NodeJS.Timeout>();

  // Calculate item positions
  const itemPositions = useMemo<ItemPosition[]>(() => {
    const positions: ItemPosition[] = [];
    let offset = 0;

    for (let i = 0; i < items.length; i++) {
      const height = typeof itemHeight === 'function' 
        ? itemHeight(i) 
        : itemHeight;
      
      positions.push({
        index: i,
        offset,
        height
      });
      
      offset += height;
    }

    return positions;
  }, [items, itemHeight]);

  // Calculate total height
  const totalHeight = useMemo(() => {
    if (itemPositions.length === 0) return 0;
    const lastItem = itemPositions[itemPositions.length - 1];
    return lastItem.offset + lastItem.height;
  }, [itemPositions]);

  // Calculate visible range
  const visibleRange = useMemo(() => {
    const containerHeight = height;
    
    // Find start index
    let startIndex = 0;
    for (let i = 0; i < itemPositions.length; i++) {
      if (itemPositions[i].offset + itemPositions[i].height > scrollTop) {
        startIndex = Math.max(0, i - overscan);
        break;
      }
    }

    // Find end index
    let endIndex = startIndex;
    const maxScrollTop = scrollTop + containerHeight;
    for (let i = startIndex; i < itemPositions.length; i++) {
      if (itemPositions[i].offset > maxScrollTop) {
        endIndex = Math.min(items.length - 1, i + overscan);
        break;
      }
      endIndex = i;
    }

    return { startIndex, endIndex };
  }, [scrollTop, height, itemPositions, overscan, items.length]);

  // Handle scroll events
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const newScrollTop = target.scrollTop;
    
    setScrollTop(newScrollTop);
    setIsScrolling(true);

    // Clear existing timeout
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }

    // Set scrolling to false after scroll ends
    scrollTimeoutRef.current = setTimeout(() => {
      setIsScrolling(false);
    }, 150);

    if (onScroll) {
      onScroll(newScrollTop);
    }
  }, [onScroll]);

  // Render visible items
  const visibleItems = useMemo(() => {
    const items: React.ReactNode[] = [];
    const { startIndex, endIndex } = visibleRange;

    for (let i = startIndex; i <= endIndex; i++) {
      const item = items[i];
      const position = itemPositions[i];
      
      if (!item || !position) continue;

      items.push(
        <ItemContainer
          key={i}
          sx={{
            transform: `translateY(${position.offset}px)`,
            height: position.height
          }}
          role="listitem"
          aria-posinset={i + 1}
          aria-setsize={items.length}
        >
          {renderItem(item, i)}
        </ItemContainer>
      );
    }

    return items;
  }, [visibleRange, items, itemPositions, renderItem]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  return (
    <ScrollContainer
      ref={scrollRef}
      className={className}
      id={id}
      onScroll={handleScroll}
      sx={{
        height,
        width,
        ...(isScrolling && {
          pointerEvents: 'none'
        })
      }}
      role="list"
      aria-label={ariaLabel || 'Virtual scrolling list'}
      tabIndex={0}
    >
      <Box
        sx={{
          height: totalHeight,
          position: 'relative'
        }}
      >
        {visibleItems}
      </Box>
    </ScrollContainer>
  );
}

export default React.memo(VirtualList) as typeof VirtualList;